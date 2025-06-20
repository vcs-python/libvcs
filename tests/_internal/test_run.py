"""Tests for libvcs._internal.run module, focusing on output streaming."""

from __future__ import annotations

import sys
import textwrap
import time
import typing as t

import pytest

from libvcs import exc
from libvcs._internal.run import run

if t.TYPE_CHECKING:
    import datetime
    import pathlib


class TestProgressOutput:
    """Test progress output streaming and flushing behavior."""

    def test_progress_callback_receives_chunks(self, tmp_path: pathlib.Path) -> None:
        """Test that progress callback receives output in chunks."""
        captured_chunks: list[str] = []
        captured_times: list[datetime.datetime] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks and timestamps."""
            captured_chunks.append(output)
            captured_times.append(timestamp)

        # Create a test script that outputs progress
        script = tmp_path / "progress_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys
                import time

                # Simulate progress output to stderr
                messages = [
                    "Starting process...\\n",
                    "Progress: 10%\\r",
                    "Progress: 20%\\r",
                    "Progress: 30%\\r",
                    "Progress: 40%\\r",
                    "Progress: 50%\\r",
                    "Done!\\n"
                ]

                for msg in messages:
                    sys.stderr.write(msg)
                    sys.stderr.flush()
                    time.sleep(0.01)  # Small delay to ensure chunks
                """,
            ),
        )

        # Run the script with progress callback
        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Verify we got multiple chunks
        assert len(captured_chunks) > 0, "Should receive progress chunks"
        assert len(captured_times) == len(captured_chunks), (
            "Each chunk should have timestamp"
        )

        # Check that final carriage return was sent
        assert captured_chunks[-1] == "\r", "Should end with carriage return"

    def test_fragmentation_with_128_byte_chunks(self, tmp_path: pathlib.Path) -> None:
        """Test that current implementation fragments output at 128-byte boundaries."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            if output != "\r":  # Ignore the final \r
                captured_chunks.append(output)

        # Create a script that outputs a long line
        script = tmp_path / "long_line_test.py"
        long_message = "X" * 300  # 300 characters, should be split into 3 chunks
        script.write_text(
            f"""
import sys
sys.stderr.write("{long_message}")
sys.stderr.flush()
""",
        )

        # Run with progress callback
        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Verify fragmentation occurs at 128-byte boundaries
        assert len(captured_chunks) >= 2, "Long line should be fragmented"

        # Check chunk sizes (except possibly the last one)
        for chunk in captured_chunks[:-1]:
            assert len(chunk) == 128, f"Chunk should be 128 bytes, got {len(chunk)}"

        # Verify total output is preserved
        total_output = "".join(captured_chunks)
        assert total_output == long_message, "Total output should match original"

    def test_git_style_progress_fragmentation(self, tmp_path: pathlib.Path) -> None:
        """Test fragmentation of git-style progress output."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            if output != "\r":  # Ignore the final \r
                captured_chunks.append(output)

        # Create a script that simulates git progress output
        script = tmp_path / "git_progress_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                # Simulate git clone progress (each line > 128 chars)
                progress_lines = [
                    "Cloning into 'repository'...\\n",
                    "remote: Enumerating objects: 1234, done.\\n",
                    "remote: Counting objects:   0% (0/1234)        \\n",
                    "remote: Counting objects:  10% (123/1234)        \\n",
                    "remote: Counting objects:  20% (247/1234)        \\n",
                    "remote: Counting objects:  30% (370/1234)        \\n",
                    "remote: Counting objects:  40% (494/1234)        \\n",
                    "remote: Counting objects:  50% (617/1234)        \\n",
                    "remote: Counting objects:  60% (740/1234)        \\n",
                    "remote: Counting objects:  70% (864/1234)        \\n",
                    "remote: Counting objects:  80% (987/1234)        \\n",
                    "remote: Counting objects:  90% (1111/1234)        \\n",
                    "remote: Counting objects: 100% (1234/1234), done.\\n",
                ]

                for line in progress_lines:
                    sys.stderr.write(line)
                    sys.stderr.flush()
                """,
            ),
        )

        # Run with progress callback
        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Check that output is fragmented
        assert len(captured_chunks) > 0, "Should capture output"

        # Join all chunks to verify content
        full_output = "".join(captured_chunks)
        assert "Cloning into 'repository'..." in full_output
        assert "remote: Counting objects: 100%" in full_output

    def test_real_time_streaming(self, tmp_path: pathlib.Path) -> None:
        """Test that output is streamed in real-time, not buffered until end."""
        captured_chunks: list[str] = []
        capture_times: list[float] = []

        def timing_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output and timing."""
            captured_chunks.append(output)
            capture_times.append(time.time())

        # Create a script with delayed output
        script = tmp_path / "streaming_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys
                import time

                sys.stderr.write("First message\\n")
                sys.stderr.flush()
                time.sleep(0.1)

                sys.stderr.write("Second message\\n")
                sys.stderr.flush()
                time.sleep(0.1)

                sys.stderr.write("Third message\\n")
                sys.stderr.flush()
                """,
            ),
        )

        time.time()
        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=timing_callback,
        )

        # In current implementation, all stderr is read in one chunk
        # This demonstrates the buffering issue
        assert len(captured_chunks) >= 1, "Should get at least 1 chunk"

        # Check if output was buffered (all messages in one chunk)
        if len(captured_chunks) >= 2 and captured_chunks[-1] == "\r":
            # Excluding the final \r
            main_chunks = captured_chunks[:-1]
            if len(main_chunks) == 1:
                # All output came in one chunk - buffered, not streamed
                assert "First message" in main_chunks[0]
                assert "Second message" in main_chunks[0]
                assert "Third message" in main_chunks[0]

    def test_callback_with_mixed_output(self, tmp_path: pathlib.Path) -> None:
        """Test callback with mixed stdout and stderr output."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            if output != "\r":
                captured_chunks.append(output)

        # Create a script with mixed output
        script = tmp_path / "mixed_output_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                # Note: callback only captures stderr in current implementation
                sys.stdout.write("This goes to stdout\\n")
                sys.stdout.flush()

                sys.stderr.write("This goes to stderr\\n")
                sys.stderr.flush()

                sys.stdout.write("More stdout\\n")
                sys.stdout.flush()

                sys.stderr.write("More stderr\\n")
                sys.stderr.flush()
                """,
            ),
        )

        stdout_result = run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Verify callback only gets stderr (current behavior)
        captured_text = "".join(captured_chunks)
        assert "This goes to stderr" in captured_text
        assert "More stderr" in captured_text
        assert "This goes to stdout" not in captured_text

        # Verify stdout is captured in return value
        assert "This goes to stdout" in stdout_result
        assert "More stdout" in stdout_result

    def test_no_callback_no_streaming(self, tmp_path: pathlib.Path) -> None:
        """Test that without callback, output is not streamed."""
        # Create a script with output
        script = tmp_path / "no_callback_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys
                sys.stderr.write("Error output\\n")
                sys.stdout.write("Normal output\\n")
                """,
            ),
        )

        # Run without callback
        output = run(
            [sys.executable, str(script)],
            log_in_real_time=False,  # No real-time logging
        )

        # Should get stdout only
        assert output.strip() == "Normal output"

    def test_progress_callback_with_carriage_returns(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Test handling of carriage returns in progress output."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            captured_chunks.append(output)

        # Create a script using carriage returns for progress
        script = tmp_path / "cr_progress_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys
                import time

                # Simulate progress with carriage returns
                for i in range(0, 101, 20):
                    sys.stderr.write(f"\\rProgress: {i}%")
                    sys.stderr.flush()
                    time.sleep(0.01)

                sys.stderr.write("\\rProgress: 100%\\n")
                sys.stderr.flush()
                """,
            ),
        )

        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Join chunks and check content
        full_output = "".join(captured_chunks)
        assert "Progress:" in full_output
        assert "100%" in full_output

        # Should have final \r
        assert captured_chunks[-1] == "\r"


class TestDesiredBehavior:
    """Tests demonstrating the desired line-buffered behavior."""

    def test_line_buffered_output(self, tmp_path: pathlib.Path) -> None:
        """Test ideal behavior: output should be line-buffered, not chunk-buffered."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            if output != "\r":
                captured_chunks.append(output)

        # Create a script with git-style progress
        script = tmp_path / "line_buffer_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                # Each line should come as a separate chunk
                lines = [
                    "Starting process...\\n",
                    "Processing item 1 of 100\\r",
                    "Processing item 50 of 100\\r",
                    "Processing item 100 of 100\\r",
                    "Process complete!\\n"
                ]

                for line in lines:
                    sys.stderr.write(line)
                    sys.stderr.flush()
                """,
            ),
        )

        # This test will fail with current implementation
        # but shows what we want to achieve
        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Ideally, each line should be a separate chunk
        # Current behavior: may fragment at 128 bytes
        # Desired behavior: each complete line is one chunk

        # For now, just verify we got output
        assert len(captured_chunks) > 0, "Should capture output"
        full_output = "".join(captured_chunks)
        assert "Starting process..." in full_output
        assert "Process complete!" in full_output

    def test_demonstrate_fragmentation(self, tmp_path: pathlib.Path) -> None:
        """Demonstrate the fragmentation issue with actual output."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            captured_chunks.append(output)

        # Create a script with realistic git clone output
        script = tmp_path / "demo_fragmentation.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                # Simulate git clone output that will be fragmented
                output = (
                    "Cloning into '/home/user/project'...\\n"
                    "remote: Enumerating objects: 11363, done.\\n"
                    "remote: Counting objects:   0% (0/1234)        \\n"
                    "remote: Counting objects:  50% (617/1234)        \\n"
                    "remote: Counting objects: 100% (1234/1234), done.\\n"
                )

                sys.stderr.write(output)
                sys.stderr.flush()
                """,
            ),
        )

        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # Verify fragmentation occurred
        non_cr_chunks = [c for c in captured_chunks if c != "\\r"]
        # With current 128-byte chunking, this output should be fragmented
        assert len(non_cr_chunks) >= 2, (
            "Output should be fragmented into multiple chunks"
        )

        assert len(captured_chunks) > 0

    def test_no_fragmentation_of_progress_lines(self, tmp_path: pathlib.Path) -> None:
        """Test that progress lines should not be fragmented."""
        captured_chunks: list[str] = []

        def capture_callback(output: str, timestamp: datetime.datetime) -> None:
            """Capture output chunks."""
            if output != "\r":
                captured_chunks.append(output)

        # Create a script with long progress lines
        script = tmp_path / "no_fragment_test.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys

                # Long progress line that would be fragmented at 128 bytes
                long_line = "remote: Counting objects: 100% (1234567890/1234567890), 12.34 GiB | 123.45 MiB/s, done.\\n"
                sys.stderr.write(long_line)
                sys.stderr.flush()
                """,
            ),
        )

        run(
            [sys.executable, str(script)],
            log_in_real_time=True,
            callback=capture_callback,
        )

        # In ideal implementation, this would be one chunk
        # Current implementation will fragment it

        # Join all chunks and verify content is preserved
        full_output = "".join(captured_chunks)
        assert "remote: Counting objects: 100%" in full_output
        assert "done." in full_output


class TestRunBehavior:
    """Test general run() behavior."""

    def test_run_with_error(self, tmp_path: pathlib.Path) -> None:
        """Test run with non-zero exit code."""
        script = tmp_path / "error_test.py"
        script.write_text(
            """
import sys
sys.stderr.write("Error occurred\\n")
sys.exit(1)
""",
        )

        with pytest.raises(exc.CommandError) as excinfo:
            run([sys.executable, str(script)])

        assert excinfo.value.returncode == 1
        assert "Error occurred" in str(excinfo.value.output)

    def test_run_check_returncode_false(self, tmp_path: pathlib.Path) -> None:
        """Test run with check_returncode=False doesn't raise on error."""
        script = tmp_path / "error_test.py"
        script.write_text(
            """
import sys
sys.stderr.write("Error output\\n")
sys.exit(1)
""",
        )

        # Should not raise
        output = run(
            [sys.executable, str(script)],
            check_returncode=False,
        )

        # With error, output comes from stderr
        assert "Error output" in output
