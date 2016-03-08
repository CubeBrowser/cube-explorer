import param
import iris.plot as iplt
from cartopy import crs
from holoviews.core import Store, HoloMap
from holoviews.plotting.mpl import (ElementPlot, ColorbarPlot, PointPlot,
                                    OverlayPlot)

from ..element import (GeoContour, GeoImage, GeoPoints, GeoFeature,
                       WMTS, GeoTiles)


class GeoPlot(ElementPlot):
    """
    Plotting baseclass for geographic plots with a cartopy projection.
    """

    projection = param.Parameter(default=crs.PlateCarree())
    
    def __init__(self, element, **params):
        if 'projection' not in params:
            el = element.last if isinstance(element, HoloMap) else element
            params['projection'] = el.crs
        super(GeoPlot, self).__init__(element, **params)
        self.aspect = 'equal'
        self.apply_ranges = False

    def teardown_handles(self):
        """
        Until cartopy artists can be updated directly
        the bottom layer clears the axis.
        """
        if self.zorder == 0:
            self.handles['axis'].cla()
    

class GeoContourPlot(GeoPlot, ColorbarPlot):
    """
    Draws a contour or contourf plot from the data in
    a GeoContour.
    """

    filled = param.Boolean(default=True, doc="""
        Whether to draw filled or unfilled contours""")

    levels = param.ClassSelector(default=5, class_=(int, list))

    style_opts = ['antialiased', 'alpha', 'cmap']
    
    def get_data(self, element, ranges, style):
        args = (element.data,)
        if isinstance(self.levels, int):
            args += (self.levels,)
        else:
            style['levels'] = self.levels
        return args, style, {}

    def init_artists(self, ax, plot_args, plot_kwargs):
        plotfn = iplt.contourf if self.filled else iplt.contour
        artists = {'artist': plotfn(*plot_args, axes=ax, **plot_kwargs)}
        return artists
    

class GeoImagePlot(GeoPlot, ColorbarPlot):

    """
    Draws a pcolormesh plot from the data in a GeoImage Element.
    """

    style_opts = ['alpha', 'cmap', 'interpolation', 'visible',
                  'filterrad', 'clims', 'norm']

    def get_data(self, element, ranges, style):
        self._norm_kwargs(element, ranges, style, element.vdims[0])
        return (element.data,), style, {}
    
    def init_artists(self, ax, plot_args, plot_kwargs):
        return {'artist': iplt.pcolormesh(*plot_args, axes=ax, **plot_kwargs)}


class GeoPointPlot(GeoPlot, PointPlot):
    """
    Draws a scatter plot from the data in a GeoPoints Element.
    """

    
    def get_data(self, element, ranges, style):
        data = super(GeoPointPlot, self).get_data(element, ranges, style)
        args, style, axis_kwargs = data
        style['transform'] = element.crs
        return args, style, axis_kwargs


########################################
#  Geographic features and annotations #
########################################

    
class GeoFeaturePlot(GeoPlot):
    """
    Draws a feature from a GeoFeatures Element.
    """
    
    def get_data(self, element, ranges, style):
        return (element.data,), style, {}

    def init_artists(self, ax, plot_args, plot_kwargs):
        return {'artist': ax.add_feature(*plot_args)}


class WMTSPlot(GeoPlot):
    """
    Adds a Web Map Tile Service from a WMTS Element.
    """
    
    def get_data(self, element, ranges, style):
        return (element.data, element.layer), style, {}

    def init_artists(self, ax, plot_args, plot_kwargs):
        return {'artist': ax.add_wmts(*plot_args)}    
    

class GeoTilePlot(GeoPlot):
    """
    Draws image tiles specified by a GeoTiles Element.
    """

    zoom = param.Integer(default=8)
    
    def get_data(self, element, ranges, style):
        return (element.data, self.zoom), style, {}

    def init_artists(self, ax, plot_args, plot_kwargs):
        return {'artist': ax.add_image(*plot_args)}


# Register plots with HoloViews
Store.register({GeoContour: GeoContourPlot,
                GeoImage: GeoImagePlot,
                GeoFeature: GeoFeaturePlot,
                WMTS: WMTSPlot,
                GeoTiles: GeoTilePlot,
                GeoPoints: GeoPointPlot}, 'matplotlib')


# Define plot and style options
opts = Store.options(backend='matplotlib')
OverlayPlot.aspect = 'equal'
