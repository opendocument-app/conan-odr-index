from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMakeToolchain, CMakeDeps, CMake, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get
)
from conan.tools.scm import Version


class OpenDocumentCoreConan(ConanFile):
    name = "odrcore"
    version = ""
    url = "https://github.com/opendocument-app/OpenDocument.core"
    homepage = "https://opendocument.app/"
    description = "C++ library that translates office documents to HTML"
    topics = "open document", "openoffice xml", "open document reader"
    license = "MPL-2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pdf2htmlEX": [True, False],
        "with_wvWare": [True, False],
        "with_libmagic": [True, False],
        "with_http_server": [True, False],
        "with_cli": [True, False],
        "with_python": [True, False],
        "with_jni": [True, False],
        "bundle_assets": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pdf2htmlEX": True,
        "with_wvWare": True,
        "with_libmagic": True,
        "with_http_server": True,
        "with_cli": True,
        "with_python": False,
        "with_jni": False,
        "bundle_assets": True,
    }

    def config_options(self):
        # Drop options that the requested core does not know about yet, so they
        # cannot be set to a value that silently has no effect. The upstream
        # CMake option each one drives appeared in:
        #   WITH_LIBMAGIC          -> 5.1.0 (no libmagic support at all before)
        #   ODR_BUNDLE_ASSETS      -> 5.3.0 (assets were always installed before)
        #   ODR_WITH_HTTP_SERVER   -> 5.4.1 (cpp-httplib was a hard dependency)
        #   ODR_PYTHON / ODR_JNI   -> 5.7.0 (bindings did not exist before)
        # ODR_CLI is far older than any of these, but only from 5.7.0 does the
        # install step skip the cli targets it did not build - turning it off in
        # an older core just breaks packaging.
        version = Version(self.version)
        if version < "5.1.0":
            del self.options.with_libmagic
        if version < "5.3.0":
            del self.options.bundle_assets
        if version < "5.4.1":
            del self.options.with_http_server
        if version < "5.7.0":
            del self.options.with_cli
            del self.options.with_python
            del self.options.with_jni
        if self.settings.os == "Windows":
            del self.options.fPIC
            # @TODO: ideally Windows should just default_options['with_pdf2htmlEX'] = False
            # But by the time config_options() is executed, default_options is already done parsed.
            del self.options.with_pdf2htmlEX
            del self.options.with_wvWare
            self.options.rm_safe("with_libmagic")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("pugixml/1.15")
        self.requires("cryptopp/8.9.0")
        self.requires("miniz/3.0.2")
        self.requires("nlohmann_json/3.12.0")
        self.requires("vincentlaucsb-csv-parser/2.3.0")
        self.requires("uchardet/0.0.8")
        self.requires("utfcpp/4.0.8")
        self.requires("argon2/20190702-odr")

        # Cores before 5.4.1 have no option for it and link cpp-httplib always.
        if self.options.get_safe("with_http_server", True):
            self.requires("cpp-httplib/0.28.0")
        if self.options.get_safe("with_pdf2htmlEX"):
            # pdf2htmlex pins poppler/fontforge transitively. The newer build
            # (732fd68 -> poppler 26.05.0-odr, fontforge 20251009) is only
            # compatible with odrcore >= 5.3.0; older cores need the previous
            # pdf2htmlex (eb5d291 -> poppler 24.08.0-odr, fontforge 20240423-git).
            if Version(self.version) >= "5.3.0":
                self.requires("pdf2htmlex/0.18.8.rc1-odr-git-732fd68")
            else:
                self.requires("pdf2htmlex/0.18.8.rc1-odr-git-eb5d291")
        if self.options.get_safe("with_wvWare"):
            self.requires("wvware/1.2.9-odr")
        if self.options.get_safe("with_libmagic", False):
            self.requires("libmagic/5.45")
        if self.options.get_safe("with_python", False):
            self.requires("pybind11/2.13.6")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def validate_build(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, 20)

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
        tc.variables["WITH_LIBMAGIC"] = self.options.get_safe("with_libmagic", False)
        tc.variables["ODR_WITH_HTTP_SERVER"] = self.options.get_safe("with_http_server", True)
        # Consumers that only link the library (e.g. the mobile apps) can drop the
        # cli tools, which otherwise get built and installed with the package.
        tc.variables["ODR_CLI"] = self.options.get_safe("with_cli", True)
        tc.variables["ODR_PYTHON"] = self.options.get_safe("with_python", False)
        tc.variables["ODR_JNI"] = self.options.get_safe("with_jni", False)
        # Consumers that ship the third-party data files themselves and wire the
        # paths at runtime (e.g. via odr::GlobalParams) can set this to False to
        # skip bundling them into the odrcore package at build time.
        tc.variables["ODR_BUNDLE_ASSETS"] = self.options.get_safe("bundle_assets", True)

        # When ODR_BUNDLE_ASSETS is on, odrcore's CMake copies third-party data
        # files (fontconfig/poppler/pdf2htmlEX data, magic.mgc) into its own data
        # dir and needs their source paths at configure time. It never discovers
        # them itself, so bridge them from the dependencies' runenv (exported by
        # their package_info()); otherwise the build fails fast (issue #599).
        runenv_info = Environment()
        for dep in self.dependencies.host.topological_sort.values():
            runenv_info.compose_env(dep.runenv_info)
        envvars = runenv_info.vars(self)
        tc.variables["FONTCONFIG_DATA_PATH"] = envvars.get("FONTCONFIG_PATH")
        tc.variables["POPPLER_DATA_PATH"] = envvars.get("POPPLER_DATA_DIR")
        tc.variables["PDF2HTMLEX_DATA_PATH"] = envvars.get("PDF2HTMLEX_DATA_DIR")
        tc.variables["LIBMAGIC_DATABASE_PATH"] = envvars.get("MAGIC")

        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["odr"]
