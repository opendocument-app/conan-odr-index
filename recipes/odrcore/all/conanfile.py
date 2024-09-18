import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get, copy
)
from conan.tools.scm import Version


class OpenDocumentCoreConan(ConanFile):
    name = "odrcore"
    version = ""
    url = "https://github.com/opendocument-app/OpenDocument.core"
    homepage = "https://opendocument.app/"
    description = "C++ library that translates office documents to HTML"
    topics = "open document", "openoffice xml", "open document reader"
    license = "GPL 3.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pdf2htmlEX": [True, False],
        "with_wvWare": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pdf2htmlEX": True,
        "with_wvWare": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            # @TODO: ideally Windows should just default_options['with_pdf2htmlEX'] = False
            # But by the time config_options() is executed, default_options is already done parsed.
            del self.options.with_pdf2htmlEX
            del self.options.with_wvWare
        elif self.version != "4.1.0-pdf2htmlex-git":
            del self.options.with_pdf2htmlEX
            del self.options.with_wvWare

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        if Version(self.version) <= "2.0.0":
            return

        self.requires("pugixml/1.14")
        self.requires("cryptopp/8.9.0")
        self.requires("miniz/3.0.2")
        self.requires("nlohmann_json/3.11.3")
        self.requires("vincentlaucsb-csv-parser/2.3.0")
        self.requires("uchardet/0.0.8")
        self.requires("utfcpp/4.0.4")
        if self.options.get_safe("with_pdf2htmlEX"):
            self.requires("pdf2htmlex/0.18.8.rc1-git-6f85c88")
        if self.options.get_safe("with_wvWare"):
            self.requires("wvware/1.2.9")

    def build_requirements(self):
        if Version(self.version) <= "2.0.0":
            return

        self.test_requires("gtest/1.14.0")

    def validate_build(self):
        if self.settings.get_safe("compiler.cppstd"):
            if Version(self.version) >= "4.0.0":
                check_min_cppstd(self, 20)
            elif Version(self.version) >= "2.0.0":
                check_min_cppstd(self, 17)
            else:
                check_min_cppstd(self, 14)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version]["source"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_PROJECT_VERSION"] = self.version
        tc.variables["ODR_TEST"] = False
        tc.variables["WITH_PDF2HTMLEX"] = self.options.get_safe("with_pdf2htmlEX", False)
        tc.variables["WITH_WVWARE"] = self.options.get_safe("with_wvWare", False)
        if Version(self.version) <= "4.0.0":
            tc.variables["CONAN_EXPORTED"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Not needed with CMake changes in 4.1.0-pdf2htmlex-git
        # Other versions may not need it too
        if self.version != "4.1.0-pdf2htmlex-git":
            copy(
                self,
                "*.hpp",
                src=os.path.join(self.recipe_folder, "src"),
                dst=os.path.join(self.export_sources_folder, "include"),
            )

        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        if Version(self.version) >= "2.1.0":
            self.cpp_info.libs = ["odr"]
        elif Version(self.version) == "2.0.0":
            self.cpp_info.libs = ["odr-static"]
        else:
            self.cpp_info.libs = ["odrlib"]
