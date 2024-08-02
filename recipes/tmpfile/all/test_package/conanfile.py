import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class FontForgeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def layout(self):
        cmake_layout(self)

    def test(self):
        if self.settings.os == "Android":
            bin_path = os.path.join(self.cpp.build.bindir, "tmpfile_tests")
            uploaded_dir = "/data/local/tmp/tmpfile-test"

            if self.run(f"adb shell mkdir {uploaded_dir}", env="conanrun", ignore_errors=True) == 0:
                self.run(f"adb push {bin_path} {uploaded_dir}/tmpfile_tests", env="conanrun")

                # Testcases described in
                # https://github.com/ViliusSutkus89/tmpfile-Android/blob/v3.0.6/tests/src/androidTest/java/com/viliussutkus89/android/tmpfile/tests/StandaloneEXEInstrumentedTests.java
                for i in range(1, 7):
                    print(f"Running testcase {i}")
                    self.run(f"adb shell {uploaded_dir}/tmpfile_tests {i}", env="conanrun")

                self.run(f"adb shell rm -r {uploaded_dir}", env="conanrun")
