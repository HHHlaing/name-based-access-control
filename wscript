# -*- Mode: python; py-indent-offset: 4; indent-tabs-mode: nil; coding: utf-8; -*-

from waflib import Context, Logs, Utils
import os, subprocess

VERSION = '0.1.0'
APPNAME = 'ndn-nac'
PACKAGE_BUGREPORT = "http://redmine.named-data.net/projects/nac"
GIT_TAG_PREFIX = "ndn-nac-"

def options(opt):
    opt.load(['compiler_c', 'compiler_cxx', 'gnu_dirs'])
    opt.load(['boost', 'default-compiler-flags', 'sanitizers', 'coverage', 'doxygen'],
             tooldir=['.waf-tools'])

    opt = opt.add_option_group ("NDN-NAC Options")

    opt.add_option('--with-tests', action='store_true', default=False, dest='with_tests',
                   help='''Build unit tests''')

def configure(conf):
    conf.load(['compiler_c', 'compiler_cxx', 'gnu_dirs', 'boost', 'default-compiler-flags', 'sanitizers', 'doxygen'])

    conf.env['WITH_TESTS'] = conf.options.with_tests

    if 'PKG_CONFIG_PATH' not in os.environ:
        os.environ['PKG_CONFIG_PATH'] = Utils.subst_vars('${LIBDIR}/pkgconfig', conf.env)
    conf.check_cfg(package='libndn-cxx', args=['--cflags', '--libs'],
                   uselib_store='NDN_CXX', mandatory=True)

    boost_libs = 'system iostreams'
    if conf.env['WITH_TESTS']:
        conf.define('NDN_NAC_HAVE_TESTS', 1);
        boost_libs += ' unit_test_framework'

    conf.check_boost(lib=boost_libs)

    conf.check_compiler_flags()

    # Loading "late" to prevent tests from being compiled with profiling flags
    conf.load('coverage')

    conf.load('sanitizers')

    conf.define('SYSCONFDIR', conf.env['SYSCONFDIR'])
    
    conf.write_config_header('config.hpp')

def build(bld):
    version(bld)

    bld.shlib(
        target="libndn-nac",
        vnum=VERSION_BASE,
        cnum=VERSION_BASE,
        source =  bld.path.ant_glob(['src/**/*.cpp']),
        use = 'BOOST NDN_CXX CRYPTOPP',
        includes = ['src', '.'],
        export_includes=['src', '.'])

    # Unit tests
    if bld.env['WITH_TESTS']:
        bld.recurse('tests')

    bld.install_files(
        dest = "%s/ndn-group-encrypt" % bld.env['INCLUDEDIR'],
        files = bld.path.ant_glob(['src/**/*.hpp', 'src/**/*.h', 'common.hpp']),
        cwd = bld.path.find_dir("src"),
        relative_trick = True)

    bld.install_files(
        dest = "%s/ndn-group-encrypt" % bld.env['INCLUDEDIR'],
        files = bld.path.get_bld().ant_glob(['src/**/*.hpp', 'common.hpp', 'config.hpp']),
        cwd = bld.path.get_bld().find_dir("src"),
        relative_trick = False )

    bld(features = "subst",
        source='libndn-nac.pc.in',
        target='libndn-nac.pc',
        install_path = '${LIBDIR}/pkgconfig',
        PREFIX       = bld.env['PREFIX'],
        INCLUDEDIR   = "%s/ndn-nac" % bld.env['INCLUDEDIR'],
        VERSION      = VERSION)

def docs(bld):
    from waflib import Options
    Options.commands = ['doxygen', 'sphinx'] + Options.commands

def doxygen(bld):
    version(bld)

    if not bld.env.DOXYGEN:
        bld.fatal('Cannot build documentation ("doxygen" not found in PATH)')

    bld(features='subst',
        name='doxygen.conf',
        source=['docs/doxygen.conf.in',
                'docs/named_data_theme/named_data_footer-with-analytics.html.in'],
        target=['docs/doxygen.conf',
                'docs/named_data_theme/named_data_footer-with-analytics.html'],
        VERSION=VERSION,
        HTML_FOOTER='../build/docs/named_data_theme/named_data_footer-with-analytics.html' \
                        if os.getenv('GOOGLE_ANALYTICS', None) \
                        else '../docs/named_data_theme/named_data_footer.html',
        GOOGLE_ANALYTICS=os.getenv('GOOGLE_ANALYTICS', ''))

    bld(features='doxygen',
        doxyfile='docs/doxygen.conf',
        use='doxygen.conf')

def sphinx(bld):
    version(bld)

    if not bld.env.SPHINX_BUILD:
        bld.fatal('Cannot build documentation ("sphinx-build" not found in PATH)')

    bld(features='sphinx',
        config='docs/conf.py',
        outdir='docs',
        source=bld.path.ant_glob('docs/**/*.rst'),
        VERSION=VERSION)

def version(ctx):
    # don't execute more than once
    if getattr(Context.g_module, 'VERSION_BASE', None):
        return

    Context.g_module.VERSION_BASE = Context.g_module.VERSION
    Context.g_module.VERSION_SPLIT = VERSION_BASE.split('.')

    # first, try to get a version string from git
    gotVersionFromGit = False
    try:
        cmd = ['git', 'describe', '--always', '--match', '%s*' % GIT_TAG_PREFIX]
        out = subprocess.check_output(cmd, universal_newlines=True).strip()
        if out:
            gotVersionFromGit = True
            if out.startswith(GIT_TAG_PREFIX):
                Context.g_module.VERSION = out.lstrip(GIT_TAG_PREFIX)
            else:
                # no tags matched
                Context.g_module.VERSION = '%s-commit-%s' % (VERSION_BASE, out)
    except subprocess.CalledProcessError:
        pass

    versionFile = ctx.path.find_node('VERSION')
    if not gotVersionFromGit and versionFile is not None:
        try:
            Context.g_module.VERSION = versionFile.read()
            return
        except EnvironmentError:
            pass

    # version was obtained from git, update VERSION file if necessary
    if versionFile is not None:
        try:
            if versionFile.read() == Context.g_module.VERSION:
                # already up-to-date
                return
        except EnvironmentError as e:
            Logs.warn('%s exists but is not readable (%s)' % (versionFile, e.strerror))
    else:
        versionFile = ctx.path.make_node('VERSION')

    try:
        versionFile.write(Context.g_module.VERSION)
    except EnvironmentError as e:
        Logs.warn('%s is not writable (%s)' % (versionFile, e.strerror))

def dist(ctx):
    version(ctx)

def distcheck(ctx):
    version(ctx)
