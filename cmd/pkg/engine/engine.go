package engine

import (
	log "github.com/sirupsen/logrus"
)

//lint:file-ignore ST1006 'this' is package-specific

type EngineContext interface {
	ScheduleParallel(task func())
	ScheduleSerial(task func())
	WaitTasksCompleted()
	WriteRawFile(fileName string, data []byte, isWin1251 ...bool)
	Close()
}

func NewEngineContext(queueSize, poolSize int, logger *log.Entry) EngineContext {
	return newEngineContext(queueSize, poolSize, logger)
}
