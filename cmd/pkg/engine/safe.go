package engine

import (
	"errors"
	"fmt"
	"runtime/debug"

	log "github.com/sirupsen/logrus"
)

func SafeCall(function func(), name string, logger *log.Entry) {
	defer safe(func(err error) {
		logger.Errorf("Plugin %s has panic: %s", name, err)
	})()
	function()
}

type panicError struct {
	err       error
	backtrace string
}

func safe(cb func(err error)) func() {
	return func() {
		if r := recover(); r != nil {
			var err error
			switch x := r.(type) {
			case string:
				err = errors.New(x)
			case error:
				err = x
			default:
				err = fmt.Errorf("unknown error %v", x)
			}
			cb(newPanicError(err))
		}
	}
}

func newPanicError(err error) error {
	return &panicError{
		err:       err,
		backtrace: string(debug.Stack())}
}

func (e *panicError) Error() string {
	return fmt.Sprintf("err=%v\npanic:\n%s", e.err, e.backtrace)
}

func (e *panicError) Unwrap() error {
	return e.err
}
