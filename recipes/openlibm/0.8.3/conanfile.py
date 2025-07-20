import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0.6"


class OpenLibmConan(ConanFile):
    name = "openlibm"
    package_type = "library"

    license = ["MIT", "ISC", "FreeBSD/2-clause BSD/Simplified BSD License", "FDLIBM"]
    homepage = "https://openlibm.org/"
    url = "https://github.com/opendocument-app/conan-odr-index"
    description = "OpenLibm is an effort to have a high quality, portable, standalone C mathematical library (libm)"
    topics = ("math", "complex math")

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("OpenLibm does not support Windows")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.libs = ["openlibm"]
