package engine

import (
	"os"
	"path/filepath"
	"runtime/debug"
	"sync"
	"sync/atomic"
	"time"

	"golang.org/x/text/encoding/charmap"

	log "github.com/sirupsen/logrus"
)

//lint:file-ignore ST1006 'this' is package-specific

type worker struct {
	num       int
	tasks     atomic.Value
	queueSize int32
}

type engineContext struct {
	logger           *log.Entry
	pool             []worker
	poolDone         *sync.WaitGroup
	closed           int32
	files            map[string]*os.File
	mutex            *sync.Mutex
	serialWorker     worker
	serialWorkerDone *sync.WaitGroup
	progress         uint32
}

func newEngineContext(queueSize, poolSize int, logger *log.Entry) *engineContext {
	logger = logger.WithField("name", "EngineContext")
	logger.Infof("start workers poolSize=%d queueSize=%d", poolSize, queueSize)

	this := &engineContext{
		logger:           logger,
		pool:             make([]worker, poolSize),
		poolDone:         &sync.WaitGroup{},
		closed:           0,
		files:            make(map[string]*os.File),
		mutex:            &sync.Mutex{},
		serialWorker:     worker{queueSize: 0},
		serialWorkerDone: &sync.WaitGroup{},
		progress:         0,
	}

	// start threads
	this.poolDone.Add(poolSize)
	for i := 0; i < poolSize; i++ {
		this.pool[i] = this.createWorker(i, queueSize)
		this.startWorker(&this.pool[i], this.poolDone)
	}
	this.serialWorkerDone.Add(1)
	this.serialWorker = this.createWorker(0, queueSize)
	this.startWorker(&this.serialWorker, this.serialWorkerDone)
	return this
}

func (this *engineContext) createWorker(num, queueSize int) worker {
	w := worker{num: num, queueSize: 0}
	c := make(chan func(), queueSize)
	w.tasks.Store(c)
	return w
}

func (this *engineContext) checkWorkerReady(w *worker) {
	ready := make(chan bool, 1)
	acquireChan(w) <- func() { ready <- true }
	<-ready
}

func (this *engineContext) startWorker(w *worker, completed *sync.WaitGroup) {
	go this.listen(w, completed)
	this.checkWorkerReady(w)
}

func (this *engineContext) listen(w *worker, completed *sync.WaitGroup) {
	l := this.logger.WithField("num", w.num)
	l.Info("worker started")
	processed := uint32(0)
	ct := time.Now()
	for t := range getChan(w) {
		t()
		processed += 1
		qs := atomic.AddInt32(&w.queueSize, -1)
		total_processed := atomic.AddUint32(&this.progress, 1)
		if nct := time.Now(); nct.After(ct.Add(time.Second * 600)) {
			ct = nct
			l.WithField("processed", processed).WithField("queueSize", qs).WithField("total", total_processed).Info("progress")
		}
		if qs < 0 {
			l.WithField("processed", processed).WithField("queueSize", qs).Fatal("internal logic error: negative queue size")
		}
	}
	total_processed := atomic.LoadUint32(&this.progress)
	l.WithField("processed", processed).WithField("queueSize", w.queueSize).WithField("total", total_processed).Info("worker stopped")
	completed.Done()
}

func (this *engineContext) closeWorker(w *worker) {
	var empty chan func()
	if v, ok := w.tasks.Swap(empty).(chan func()); ok && v != nil {
		this.logger.WithField("num", w.num).Info("close worker")
		close(v)
	}
}

func getChan(w *worker) chan func() {
	if v, ok := w.tasks.Load().(chan func()); ok {
		return v
	}
	return nil
}

func acquireChan(w *worker) chan func() {
	if c := getChan(w); c != nil {
		atomic.AddInt32(&w.queueSize, 1)
		return c
	}
	return nil
}

func (this *engineContext) poolWorker() chan func() {
	idx := 0
	minQueue := atomic.LoadInt32(&this.pool[idx].queueSize)
	for i := range this.pool {
		if v := atomic.LoadInt32(&this.pool[i].queueSize); v < minQueue {
			minQueue = v
			idx = i
		}
	}
	return acquireChan(&this.pool[idx])
}

// call this func after all tasks have already been scheduled
func (this *engineContext) WaitTasksCompleted() {
	for i := 0; i < len(this.pool); i++ {
		this.checkWorkerReady(&this.pool[i])
	}
}

func (this *engineContext) close() {
	if !atomic.CompareAndSwapInt32(&this.closed, 0, 1) {
		this.logger.Info("already closed context")
		return
	}

	// close and wait for all workers
	count := len(this.pool)
	this.logger.Info("close context")
	// execute in each worker fake task to ensure all tasks are scheduled
	// (some tasks may do scheduling)
	this.WaitTasksCompleted()

	this.logger.Info("close workers")
	for i := 0; i < count; i++ {
		this.closeWorker(&this.pool[i])
	}
	this.logger.Info("wait workers")
	this.poolDone.Wait()
	for i := 0; i < count; i++ {
		if qs := this.pool[i].queueSize; qs != 0 {
			this.logger.WithField("worker", i).WithField("queueSize", qs).Fatal("internal logic error: worker queue is not empty")
		}
	}

	// wait for all file operations done
	this.logger.Info("close serial worker")
	this.closeWorker(&this.serialWorker)
	this.logger.Info("wait serial worker")
	this.serialWorkerDone.Wait()
	this.logger.Info("close context done")
	if qs := this.serialWorker.queueSize; qs != 0 {
		this.logger.WithField("queueSize", qs).Fatal("internal logic error: worker queue is not empty")
	}

	// close generic files
	for name, file := range this.files {
		logger := this.logger.WithField("file", name)
		logger.Info("close file")
		if err := file.Sync(); err != nil {
			logger.WithError(err).Fatal("failed to sync file")
		}
		if err := file.Close(); err != nil {
			logger.WithError(err).Fatal("failed to close file")
		}
		delete(this.files, name)
	}
}

// ////////////////////////////////////////////
// iface: ParallelWorkContext
func (this *engineContext) ScheduleParallel(task func()) {
	if w := this.poolWorker(); w != nil {
		w <- task
	} else {
		bt := string(debug.Stack())
		this.logger.Fatalf("internal logic error: call ScheduleParallel after Close: %s", bt)
	}
}

func (this *engineContext) ScheduleSerial(task func()) {
	if w := acquireChan(&this.serialWorker); w != nil {
		w <- task
	} else {
		bt := string(debug.Stack())
		this.logger.Fatalf("internal logic error: call ScheduleSerial after Close: %s", bt)
	}
}

func (this *engineContext) Close() {
	this.close()
}

func (this *engineContext) rawOpenFile(name string) *os.File {
	if dir, _ := filepath.Split(name); dir != "" {
		if err := os.MkdirAll(dir, 0755); err != nil {
			this.logger.WithField("dir", dir).WithError(err).Fatal("failed to create dir")
		}
	}
	mode := os.O_WRONLY | os.O_CREATE | os.O_TRUNC
	file, err := os.OpenFile(name, mode, 0644)
	if err != nil {
		this.logger.WithField("file", name).WithError(err).Fatal("failed to create file")
	}
	return file
}

func (this *engineContext) WriteRawFile(fileName string, data []byte, isWin1251 ...bool) {
	if len(isWin1251) != 0 && isWin1251[0] {
		this.writeWin1251(fileName, data)
		return
	}
	this.write(fileName, data)
}

func (this *engineContext) write(fileName string, data []byte) {
	this.ScheduleSerial(func() {
		var file *os.File
		if file = this.files[fileName]; file == nil {
			file = this.rawOpenFile(fileName)
			this.files[fileName] = file
		}
		if _, err := file.Write(data); err != nil {
			this.logger.WithField("file", fileName).WithError(err).Error("failed to write file")
		}
	})
}

func (this *engineContext) writeWin1251(fileName string, data []byte) {
	this.ScheduleSerial(func() {
		var file *os.File
		if file = this.files[fileName]; file == nil {
			file = this.rawOpenFile(fileName)
			this.files[fileName] = file
		}
		encoder := charmap.Windows1251.NewEncoder()
		writerWin1251 := encoder.Writer(file)
		isErrorWritten := false
		for bytesWritten := 0; ; {
			num, err := writerWin1251.Write(data[bytesWritten:])
			bytesWritten += num + 1
			if err == nil || bytesWritten >= len(data) {
				break
			}
			if !isErrorWritten {
				this.logger.WithField("file", fileName).WithError(err).Errorf("failed to write file, data: %s", string(data))
				isErrorWritten = true
			}
		}
	})
}
