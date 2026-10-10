//go:build !windows

package main

import "os/exec"

func hideWindow(cmd *exec.Cmd) {}

func selectModule(name string) error { return nil }
