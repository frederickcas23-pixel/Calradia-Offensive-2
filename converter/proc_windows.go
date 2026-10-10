//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
)

func hideWindow(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true, CreationFlags: 0x08000000}
}

// selectModule makes Warband's launcher open with this module chosen (it remembers the last module in the registry).
func selectModule(name string) error {
	reg := filepath.Join(os.Getenv("SystemRoot"), "System32", "reg.exe")
	cmd := exec.Command(reg, "add", `HKCU\Software\MountAndBlade Warband`, "/v", "last_module_warband", "/t", "REG_SZ", "/d", name, "/f")
	hideWindow(cmd)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("%v: %s", err, out)
	}
	return nil
}
