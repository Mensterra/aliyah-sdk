"""
Resource attribute semantic conventions for Aaliyah.

This module defines standard resource attributes used to identify resources in
Aaliyah telemetry data.
"""


class ResourceAttributes:
    """
    Resource attributes for Aaliyah.

    These attributes provide standard identifiers for resources being monitored
    or interacted with by Aaliyah.
    """

    # Project identifier - uniquely identifies an Aaliyah project
    PROJECT_ID = "aaliyah.project.id"

    # Service attributes
    SERVICE_NAME = "service.name"
    SERVICE_VERSION = "service.version"

    # Environment attributes
    ENVIRONMENT = "aaliyah.environment"
    DEPLOYMENT_ENVIRONMENT = "deployment.environment"

    # SDK attributes
    SDK_NAME = "aaliyah.sdk.name"
    SDK_VERSION = "aaliyah.sdk.version"

    # Host machine attributes
    HOST_MACHINE = "host.machine"
    HOST_NAME = "host.name"
    HOST_NODE = "host.node"
    HOST_OS_RELEASE = "host.os_release"
    HOST_PROCESSOR = "host.processor"
    HOST_SYSTEM = "host.system"
    HOST_VERSION = "host.version"

    # CPU attributes
    CPU_COUNT = "cpu.count"
    CPU_PERCENT = "cpu.percent"

    # Memory attributes
    MEMORY_TOTAL = "memory.total"
    MEMORY_AVAILABLE = "memory.available"
    MEMORY_USED = "memory.used"
    MEMORY_PERCENT = "memory.percent"

    # Libraries
    IMPORTED_LIBRARIES = "imported_libraries"
