import param
import numpy as np
import iris.plot as iplt

from matplotlib import ticker
from cartopy import crs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from holoviews.core import Store, HoloMap
from holoviews.plotting.mpl import (ElementPlot, ColorbarPlot, PointPlot,
                                    OverlayPlot, AnnotationPlot, TextPlot)

from ..element import (Contours, Image, Points, GeoFeature,
                       WMTS, GeoTiles, Text, util)


def transform_extents(element, proj, extents):
    geo_dims = element.dimensions(label=True)[0:2]
    if not getattr(element, 'crs') or len(geo_dims) != 2:
        return extents
    l, b, r, t = extents
    if type(proj) != type(element.crs):
        try:
            l, b = proj.transform_point(l, b, src_crs=element.crs)
        except:
            l, b = None, None
        try:
            r, t = proj.transform_point(r, t, src_crs=element.crs)
        except:
            r, t = None, None
    if isinstance(proj, crs._CylindricalProjection):
        l, r = l-180, r-180
    return l, b, r, t


class GeoPlot(ElementPlot):
    """
    Plotting baseclass for geographic plots with a cartopy projection.
    """

    aspect = param.ClassSelector(default='equal',
                                 class_=(util.basestring, float, int))

    projection = param.Parameter(default=crs.PlateCarree())

    show_grid = param.Boolean(default=False)

    def __init__(self, element, **params):
        if 'projection' not in params:
            el = element.last if isinstance(element, HoloMap) else element
            params['projection'] = el.crs
        super(GeoPlot, self).__init__(element, **params)


    def get_extents(self, view, ranges):
        """
        Gets the extents for the axes from the current View. The globally
        computed ranges can optionally override the extents.
        """
        extents = super(GeoPlot, self).get_extents(view, ranges)
        return transform_extents(view, self.handles['axis'].projection, extents)


    def _set_axis_ticks(self, axis, ticks, log=False, rotation=0):
        """
        Allows setting the ticks for a particular axis either with
        a tuple of ticks, a tick locator object, an integer number
        of ticks, a list of tuples containing positions and labels
        or a list of positions. Also supports enabling log ticking
        if an integer number of ticks is supplied and setting a
        rotation for the ticks.
        """
        if axis.axis_name == 'x':
            set_fn = axis.axes.set_xticks
            low, high = axis.axes.get_xlim()
            formatter = LongitudeFormatter(number_format='.3g')
        else:
            set_fn = axis.axes.set_yticks
            low, high = axis.axes.get_ylim()
            formatter = LatitudeFormatter(number_format='.3g')

        if isinstance(ticks, ticker.Locator):
            axis.set_major_locator(ticks)
        elif not ticks and ticks is not None:
            axis.set_ticks([])
        elif isinstance(ticks, int):
            axis.set_major_formatter(formatter)
            ticks = list(np.linspace(low, high, ticks))
            set_fn(ticks, crs=crs.PlateCarree())
        elif isinstance(ticks, (list, tuple)):
            labels = None
            if all(isinstance(t, tuple) for t in ticks):
                ticks, labels = zip(*ticks)
            set_fn(ticks, crs=crs.PlateCarree())
            if labels:
                axis.set_ticklabels(labels)
            else:
                axis.set_major_formatter(formatter)

        if ticks:
            for tick in axis.get_ticklabels():
                tick.set_rotation(rotation)


    def teardown_handles(self):
        """
        Removes artist from figure so it can be redrawn.
        Some plots clear entire axis, so ValueErrors are
        caught in case the object has already been removed.
        """
        if 'artist' in self.handles:
            try:
                self.handles['artist'].remove()
            except ValueError:
                pass


class GeoContourPlot(GeoPlot, ColorbarPlot):
    """
    Draws a contour or contourf plot from the data in
    a Contours.
    """

    filled = param.Boolean(default=True, doc="""
        Whether to draw filled or unfilled contours""")

    levels = param.ClassSelector(default=5, class_=(int, list))

    style_opts = ['antialiased', 'alpha', 'cmap']
    
    def get_data(self, element, ranges, style):
        args = (element.data.copy(),)
        if isinstance(self.levels, int):
            args += (self.levels,)
        else:
            style['levels'] = self.levels
        return args, style, {}

    def teardown_handles(self):
        """
        Until cartopy artists can be updated directly
        the bottom layer clears the axis.
        """
        if self.zorder == 0:
            self.handles['axis'].cla()

    def init_artists(self, ax, plot_args, plot_kwargs):
        plotfn = iplt.contourf if self.filled else iplt.contour
        artists = {'artist': plotfn(*plot_args, axes=ax, **plot_kwargs)}
        return artists
    

class GeoImagePlot(GeoPlot, ColorbarPlot):

    """
    Draws a pcolormesh plot from the data in a Image Element.
    """

    style_opts = ['alpha', 'cmap', 'visible', 'filterrad', 'clims', 'norm']

    def get_data(self, element, ranges, style):
        self._norm_kwargs(element, ranges, style, element.vdims[0])
        style.pop('interpolation')
        return (element.data.copy(),), style, {}
    
    def init_artists(self, ax, plot_args, plot_kwargs):
        return {'artist': iplt.pcolormesh(*plot_args, axes=ax, **plot_kwargs)}


class GeoPointPlot(GeoPlot, PointPlot):
    """
    Draws a scatter plot from the data in a Points Element.
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


class GeoAnnotationPlot(AnnotationPlot):
    """
    AnnotationPlot handles the display of all annotation elements.
    """

    def initialize_plot(self, ranges=None):
        annotation = self.hmap.last
        key = self.keys[-1]
        ranges = self.compute_ranges(self.hmap, key, ranges)
        ranges = util.match_spec(annotation, ranges)
        axis = self.handles['axis']
        opts = self.style[self.cyclic_index]
        handles = self.draw_annotation(axis, annotation.data, annotation.crs, opts)
        self.handles['annotations'] = handles
        return self._finalize_axis(key, ranges=ranges)

    def update_handles(self, key, axis, annotation, ranges, style):
        # Clear all existing annotations
        for element in self.handles['annotations']:
            element.remove()

        self.handles['annotations'] = self.draw_annotation(axis,
                                                           annotation.data,
                                                           annotation.crs, style)


class GeoTextPlot(GeoAnnotationPlot, TextPlot):
    "Draw the Text annotation object"

    def draw_annotation(self, axis, data, crs, opts):
        (x,y, text, fontsize,
         horizontalalignment, verticalalignment, rotation) = data
        opts['fontsize'] = fontsize
        x, y = axis.projection.transform_point(x, y, src_crs=crs)
        return [axis.text(x, y, text,
                          horizontalalignment=horizontalalignment,
                          verticalalignment=verticalalignment,
                          rotation=rotation, **opts)]



# Register plots with HoloViews
Store.register({Contours: GeoContourPlot,
                Image: GeoImagePlot,
                GeoFeature: GeoFeaturePlot,
                WMTS: WMTSPlot,
                GeoTiles: GeoTilePlot,
                Points: GeoPointPlot,
                Text: GeoTextPlot}, 'matplotlib')


# Define plot and style options
opts = Store.options(backend='matplotlib')
OverlayPlot.aspect = 'equal'
