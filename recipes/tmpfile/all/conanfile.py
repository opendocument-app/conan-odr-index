import os

from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMake, cmake_layout, CMakeDeps
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conans.errors import ConanInvalidConfiguration

required_conan_version = ">=2.0.6"


class TmpfileConan(ConanFile):
    name = "tmpfile"
    package_type = "library"

    license = ["GPLv3"]
    homepage = "https://github.com/ViliusSutkus89/tmpfile-Android/"
    url = "https://github.com/opendocument-app/conan-odr-index"
    description = "tmpfile POSIX function fix for Android"
    topics = ("android", "posix", "workaround", "tmpfile", "bionic")

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
        if self.settings.os != "Android":
            raise ConanInvalidConfiguration("Only Android is supported")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["WITH_JNI"] = "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder='tmpfile/src/main/cpp')
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tmpfile"]
        self.cpp_info.includedirs = None
        self.cpp_info.bindirs = None
