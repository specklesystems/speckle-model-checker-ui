package logging

import (
	"fmt"
	"log"
)

// LogColor prints a colored log message using color constants from colors.go
func LogColor(color, format string, v ...interface{}) {
	msg := fmt.Sprintf(format, v...)
	log.Printf("%s%s%s", color, msg, ColorReset)
}
