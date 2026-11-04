"""ZGeo — каталог пространственных данных для QGIS."""


def classFactory(iface):
    """Точка входа QGIS-плагина."""

    from .plugin import ZGeoPlugin

    return ZGeoPlugin(iface)
