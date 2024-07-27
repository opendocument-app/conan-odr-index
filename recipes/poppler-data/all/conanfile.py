import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir

required_conan_version = ">=2.0.6"


class PopplerDataConan(ConanFile):
    name = "poppler-data"
    description = "encoding files for use with poppler, enable CJK and Cyrrilic"
    homepage = "https://poppler.freedesktop.org/"
    topics = "poppler", "pdf", "rendering"
    license = "BSD-3-Clause", "GPL-2.0-or-later", "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.settings.clear()
        self.info.clear()

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "share", "pkgconfig"))

    def package_info(self):
        self.cpp_info.resdirs = ["share/poppler"]
        # Clear out include, lib and bin dirs
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
