package logging

import (
	"fmt"
	"log"
)

// ANSI color codes
const (
	ColorReset  = "\x1b[0m"
	ColorRed    = "\x1b[31;1m"
	ColorGreen  = "\x1b[32;1m"
	ColorYellow = "\x1b[33;1m"
	ColorBlue   = "\x1b[34;1m"
	ColorPurple = "\x1b[35;1m"
	ColorCyan   = "\x1b[36;1m"
)

// LogColor prints a colored log message
func LogColor(color, format string, v ...interface{}) {
	msg := fmt.Sprintf(format, v...)
	log.Printf("%s%s%s", color, msg, ColorReset)
}
