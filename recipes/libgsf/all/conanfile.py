import os

from conan import ConanFile
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.microsoft import is_msvc, unix_path

required_conan_version = ">=2.0.6"


class LibgsfConan(ConanFile):
    name = "libgsf"
    package_type = "library"

    license = ["GPLv2"]
    homepage = "https://gitlab.gnome.org/GNOME/libgsf/"
    url = "https://github.com/opendocument-app/conan-odr-index"
    description = "The G Structured File Library"

    # Binary configuration
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # for plain C projects only
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    # def layout(self):
        # src_folder must use the same source folder name the project
        # basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("glib/2.81.0-odr", transitive_headers=True)
        self.requires("zlib/1.3.1")
        self.requires("libxml2/2.12.7", transitive_headers=True)

    # if another tool than the compiler or autotools is required to build the project (pkgconf, bison, flex etc)
    def build_requirements(self):
        # Can't exec "autopoint": No such file or directory at /home/user/.conan2/p/autocf2af015330354/p/bin/../res/autoconf/Autom4te/FileUtils.pm line 293.
        self.tool_requires("gettext/0.22.5")
        # Can't exec "gtkdocize": No such file or directory at /home/user/.conan2/p/autocf2af015330354/p/bin/../res/autoconf/Autom4te/FileUtils.pm line 293.
        # autoreconf: error: gtkdocize failed with exit status: 
        self.tool_requires("gtk-doc-stub/cci.20181216")

        # only if we have to call autoreconf
        self.tool_requires("libtool/2.4.7")
        # only if upstream configure.ac relies on PKG_CHECK_MODULES macro
        if not self.conf.get("tools.gnu:pkg_config", check_type=str):
            self.tool_requires("pkgconf/2.2.0")
        # required to suppport windows as a build machine
        if self._settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")
        # for msvc support to get compile & ar-lib scripts (may be avoided if shipped in source code of the library)
        # not needed if libtool already in build requirements
        if is_msvc(self):
            self.tool_requires("automake/1.16.5")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # apply patches listed in conandata.yml
        apply_conandata_patches(self)

    def generate(self):
        # inject tool_requires env vars in build scope (not needed if there is no tool_requires)
        env = VirtualBuildEnv(self)
        env.generate()
        # inject requires env vars in build scope
        # it's required in case of native build when there is AutotoolsDeps & at least one dependency which might be shared, because configure tries to run a test executable
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")
        # --fpic is automatically managed when 'fPIC'option is declared
        # --enable/disable-shared is automatically managed when 'shared' option is declared
        tc = AutotoolsToolchain(self)

        if self.settings.os == "Android" and self.settings.arch in ['armv7', 'x86'] and int(self.settings.os.get_safe("api_level")) < 24:
            tc.configure_args.append("--disable-largefile")

        # autotools usually uses 'yes' and 'no' to enable/disable options
        #def yes_no(v): return "yes" if v else "no"
        # tc.configure_args.extend([
            # f"--with-foobar={yes_no(self.options.with_foobar)}",
            # "--enable-tools=no",
            # "--enable-manpages=no",
        # ])
        tc.generate()
        # generate pkg-config files of dependencies (useless if upstream configure.ac doesn't rely on PKG_CHECK_MODULES macro)
        tc = PkgConfigDeps(self)
        tc.generate()
        # generate dependencies for autotools
        tc = AutotoolsDeps(self)
        tc.generate()

        # If Visual Studio is supported
        if is_msvc(self):
            env = Environment()
            # get compile & ar-lib from automake (or eventually lib source code if available)
            # it's not always required to wrap CC, CXX & AR with these scripts, it depends on how much love was put in
            # upstream build files
            automake_conf = self.dependencies.build["automake"].conf_info
            compile_wrapper = unix_path(self, automake_conf.get("user.automake:compile-wrapper", check_type=str))
            ar_wrapper = unix_path(self, automake_conf.get("user.automake:lib-wrapper", check_type=str))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} \"lib -nologo\"")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
            env.vars(self).save_script("conanbuild_msvc")

    def build(self):
        autotools = Autotools(self)
        # (optional) run autoreconf to regenerate configure file (libtool should be in tool_requires)
        autotools.autoreconf()
        # ./configure + toolchain file
        autotools.configure()
        autotools.make()

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        # some files extensions and folders are not allowed. Please, read the FAQs to get informed.
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

        # In shared lib/executable files, autotools set install_name (macOS) to lib dir absolute path instead of @rpath, it's not relocatable, so fix it
        fix_apple_shared_install_name(self)

    def package_info(self):
        self.cpp_info.libs = ["gsf-1"]
        self.cpp_info.includedirs = [os.path.join("include", "libgsf-1")]
        self.cpp_info.set_property('pkg_config_name', 'libgsf-1')
