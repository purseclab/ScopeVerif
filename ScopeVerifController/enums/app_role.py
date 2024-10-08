import enum


class AppRole(enum.Enum):
    ALPHA = "com.abc.storage_verifier_alpha"  # mostly used as "VICTIM"
    BETA = "com.abc.storage_verifier_beta"  # mostly used as "ANOTHER APP"
    GAMMA = "com.abc.storage_verifier_gamma"  # mostly used as "ATTACKER"


class ApkRole(enum.Enum):
    ALPHA = AppRole.ALPHA.value
    BETA = AppRole.BETA.value
    GAMMA = AppRole.GAMMA.value
    ACCESSIBILITY_SERVICE = "com.example.storage_accessibility_service"
