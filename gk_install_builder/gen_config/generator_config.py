"""
Configuration constants for ProjectGenerator

This module contains all configuration constants used by the ProjectGenerator.
Extracted from generator.py to improve maintainability.
"""

# Template directory (relative to generator.py location)
TEMPLATE_DIR = "templates"

# Helper directory structure
# Defines the directory structure and files to be created in the helper directory
HELPER_STRUCTURE = {
    "launchers": [
        "launcher.pos.template",
        "launcher.onex-pos.template",
        "launcher.wdm.template",
        "launcher.flow-service.template",
        "launcher.lpa-service.template",
        "launcher.storehub-service.template"
    ],
    "onboarding": [
        "pos.onboarding.json",
        "onex-pos.onboarding.json",
        "wdm.onboarding.json",
        "flow-service.onboarding.json",
        "lpa-service.onboarding.json",
        "storehub-service.onboarding.json"
    ],
    "tokens": [
        "basic_auth_password.txt",
        "form_password.txt"
    ],
    "init": [
        "get_store.json",
        {
            "storehub": [
                "update_config.json"
            ]
        }
    ]
}

# Download concurrency settings
DEFAULT_DOWNLOAD_WORKERS = 4
DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MiB

# Launcher template content
# These templates define the default configuration for each launcher type
LAUNCHER_TEMPLATE_POS = """# Launcher defaults for POS
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
hardware_package_local=
"""

LAUNCHER_TEMPLATE_ONEX_POS = """# Launcher defaults for OneX POS Client
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationJmxPort=
updaterJmxPort=
createShortcuts=0
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
hardware_package_local=
"""

LAUNCHER_TEMPLATE_WDM = """# Launcher defaults for WDM
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8080
applicationServerHttpsPort=8443
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""

LAUNCHER_TEMPLATE_FLOW_SERVICE = """# Launcher defaults for Flow Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""

LAUNCHER_TEMPLATE_LPA_SERVICE = """# Launcher defaults for LPA Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""

LAUNCHER_TEMPLATE_STOREHUB_SERVICE = """# Launcher defaults for StoreHub Service
installdir=@INSTALL_DIR@
identifierEncoded=@BASE64_TOKEN@
applicationServerHttpPort=8180
applicationServerHttpsPort=8543
applicationServerShutdownPort=8005
applicationServerJmxPort=52222
applicationJmsPort=7001
updaterJmxPort=4333
ssl_path=@SSL_PATH@
ssl_password=@SSL_PASSWORD@
firebirdServerPath=@FIREBIRD_SERVER_PATH@
firebird_driver_path_local=@FIREBIRD_DRIVER_PATH_LOCAL@
firebirdServerPort=3050
firebirdServerUser=SYSDBA
firebirdServerPassword=masterkey
identifierExpert=@OFFLINE_MODE@
useLocalFiles=@OFFLINE_MODE@
keepFiles=0
jre_package_version_local=@JRE_VERSION@
jre_package_local=@JRE_PACKAGE@
installer_package_local=@INSTALLER_PACKAGE@
tomcat_package_version_local=@TOMCAT_VERSION@
tomcat_package_local=@TOMCAT_PACKAGE@
"""

# Map launcher filenames to their templates
LAUNCHER_TEMPLATES = {
    "launcher.pos.template": LAUNCHER_TEMPLATE_POS,
    "launcher.onex-pos.template": LAUNCHER_TEMPLATE_ONEX_POS,
    "launcher.wdm.template": LAUNCHER_TEMPLATE_WDM,
    "launcher.flow-service.template": LAUNCHER_TEMPLATE_FLOW_SERVICE,
    "launcher.lpa-service.template": LAUNCHER_TEMPLATE_LPA_SERVICE,
    "launcher.storehub-service.template": LAUNCHER_TEMPLATE_STOREHUB_SERVICE
}
