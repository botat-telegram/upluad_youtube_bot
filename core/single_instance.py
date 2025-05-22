import os
import sys
import time
import atexit

class SingleInstance:
    """
    A class that ensures only one instance of the application is running at a time.
    It creates a lock file that is removed when the application exits.
    """
    def __init__(self, lock_file_path=None, timeout=5):
        self.initialized = False
        self.lockfile = lock_file_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot.lock')
        self.timeout = timeout
        self.fd = None
        
        # Make sure the lock file gets removed on exit
        atexit.register(self.cleanup)
        
        # Check if another instance is running and try to terminate it
        if self.is_running():
            try:
                with open(self.lockfile, 'r') as f:
                    old_pid = int(f.read().strip())
                try:
                    # Try to terminate the old process
                    if os.name == 'nt':  # Windows
                        import ctypes
                        kernel32 = ctypes.windll.kernel32
                        PROCESS_TERMINATE = 0x0001
                        SYNCHRONIZE = 0x00100000
                        handle = kernel32.OpenProcess(PROCESS_TERMINATE | SYNCHRONIZE, False, old_pid)
                        if handle:
                            # Try graceful termination first
                            kernel32.TerminateProcess(handle, 0)
                            # Wait for process to terminate (up to 5 seconds)
                            if kernel32.WaitForSingleObject(handle, 5000) != 0:  # WAIT_OBJECT_0 = 0
                                # Force termination if graceful attempt fails
                                kernel32.TerminateProcess(handle, 1)
                            kernel32.CloseHandle(handle)
                    else:  # Unix
                        os.kill(old_pid, 15)  # SIGTERM
                        # Wait for process to terminate (up to 5 seconds)
                        for _ in range(50):  # 50 * 0.1 = 5 seconds
                            try:
                                os.kill(old_pid, 0)  # Check if process exists
                                time.sleep(0.1)
                            except OSError:
                                break  # Process terminated
                        else:
                            # Force termination if graceful attempt fails
                            try:
                                os.kill(old_pid, 9)  # SIGKILL
                            except OSError:
                                pass  # Process already terminated
                except (ProcessLookupError, OSError):
                    pass  # Process already terminated
                
                # Try to remove the old lock file
                try:
                    os.unlink(self.lockfile)
                except OSError:
                    pass
            except Exception as e:
                print(f"Failed to terminate old instance: {e}")
                sys.exit(1)
            
        # Create the lock file
        try:
            self.fd = open(self.lockfile, 'w')
            self.fd.write(str(os.getpid()))
            self.fd.flush()
            self.initialized = True
            print(f"Lock file created at {self.lockfile}")
        except Exception as e:
            print(f"Failed to create lock file: {e}")
            sys.exit(1)
    
    def is_running(self):
        """
        Check if another instance is running by testing for the lock file.
        If the lock file exists but is stale (from a crashed instance), remove it.
        """
        if not os.path.exists(self.lockfile):
            return False
            
        # Check if the lock file is stale (older than timeout)
        if self.timeout > 0:
            if (time.time() - os.path.getmtime(self.lockfile)) > self.timeout * 60:
                print(f"Removing stale lock file (older than {self.timeout} minutes)")
                try:
                    os.unlink(self.lockfile)
                    return False
                except Exception as e:
                    print(f"Failed to remove stale lock file: {e}")
                    return True
        
        # Try to read the PID from the lock file
        try:
            with open(self.lockfile, 'r') as f:
                pid = int(f.read().strip())
                
            # Check if the process with this PID is still running
            # This is platform-specific, but works on Windows and Unix
            if os.name == 'nt':  # Windows
                import ctypes
                kernel32 = ctypes.windll.kernel32
                SYNCHRONIZE = 0x00100000
                process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                if process != 0:  # Process exists
                    kernel32.CloseHandle(process)
                    return True
                else:  # Process doesn't exist, lock file is stale
                    os.unlink(self.lockfile)
                    return False
            else:  # Unix
                try:
                    os.kill(pid, 0)  # Doesn't actually kill the process
                    return True  # Process exists
                except OSError:  # Process doesn't exist, lock file is stale
                    os.unlink(self.lockfile)
                    return False
        except Exception as e:
            print(f"Error checking lock file: {e}")
            # If we can't read the lock file, assume it's corrupted and remove it
            try:
                os.unlink(self.lockfile)
                return False
            except Exception:
                return True  # Can't remove lock file, assume another instance is running
    
    def cleanup(self):
        """Remove the lock file when the application exits."""
        if self.initialized:
            try:
                # إغلاق الملف قبل محاولة إزالته
                if self.fd:
                    self.fd.close()
                    self.fd = None
                # محاولة إزالة الملف
                if os.path.exists(self.lockfile):
                    os.unlink(self.lockfile)
            except Exception as e:
                print(f"Failed to cleanup lock file: {e}")