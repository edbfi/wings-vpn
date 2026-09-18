//go:build darwin

package ufs

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"golang.org/x/sys/unix"
)

func TestFDPathUsesOpenDescriptor(t *testing.T) {
	t.Parallel()
	original := filepath.Join(t.TempDir(), "original")
	file, err := os.Create(original)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := file.Close(); err != nil {
			t.Error(err)
		}
	})
	renamed := filepath.Join(filepath.Dir(original), "renamed")
	if err := os.Rename(original, renamed); err != nil {
		t.Fatal(err)
	}
	want, err := filepath.EvalSymlinks(renamed)
	if err != nil {
		t.Fatal(err)
	}
	got, err := fdPath(int(file.Fd()))
	if err != nil {
		t.Fatal(err)
	}
	if got != want {
		t.Fatalf("fdPath() = %q, want renamed path %q", got, want)
	}
}

func TestFDPathRejectsInvalidDescriptor(t *testing.T) {
	t.Parallel()
	if _, err := fdPath(-1); !errors.Is(err, unix.EBADF) {
		t.Fatalf("fdPath(-1) error = %v, want EBADF", err)
	}
}
