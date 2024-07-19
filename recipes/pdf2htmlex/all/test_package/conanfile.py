import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


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
        bin_path = os.path.join(self.cpp.build.bindir, "link_test")
        if can_run(self):
            self.run(bin_path, env="conanrun")

        elif self.settings.os == "Android":
            uploaded_bin_path = "/data/local/tmp/test_package"
            if self.run("adb push {} {}".format(bin_path, uploaded_bin_path), env="conanrun", ignore_errors=True) == 0:
                self.run("adb shell {}".format(uploaded_bin_path), env="conanrun")
                self.run("adb shell rm {}".format(uploaded_bin_path), env="conanrun")
