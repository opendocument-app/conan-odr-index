import os
from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get, copy
)
from conan.tools.scm import Version


class OpenDocumentCoreConan(ConanFile):
    name = "odrcore"
    url = "https://github.com/opendocument-app/OpenDocument.core"
    homepage = "https://opendocument.app/"
    description = "C++ library that translates office documents to HTML"
    topics = "open document", "openoffice xml", "open document reader"
    license = "GPL 3.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = ["cli/*", "cmake/*", "src/*", "CMakeLists.txt"]

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if Version(self.version) <= "2.0.0":
            return

        self.requires("pugixml/1.14")
        self.requires("cryptopp/8.8.0")
        self.requires("miniz/3.0.2")
        self.requires("nlohmann_json/3.11.3")
        self.requires("vincentlaucsb-csv-parser/2.1.3")
        self.requires("uchardet/0.0.7")
        self.requires("utfcpp/4.0.4")

    def build_requirements(self):
        if Version(self.version) <= "2.0.0":
            return

        self.test_requires("gtest/1.14.0")

    def validate_build(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["source"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_VERSION"] = self.version
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["ODR_TEST"] = False
        if Version(self.version) <= "4.0.0":
            tc.variables["CONAN_EXPORTED"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.recipe_folder, "src"),
            dst=os.path.join(self.export_sources_folder, "include"),
        )

        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if Version(self.version) <= "1.0.0":
            self.cpp_info.libs = ["odrlib"]
        elif Version(self.version) <= "2.0.0":
            self.cpp_info.libs = ["odr-static"]
        else:
            self.cpp_info.libs = ["odr"]
