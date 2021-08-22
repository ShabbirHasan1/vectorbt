# Copyright (c) 2021 Oleg Polakow. All rights reserved.
# This code is licensed under Apache 2.0 with Commons Clause license (see LICENSE.md for details)

"""Custom pandas accessors for OHLC(V) data.

Methods can be accessed as follows:

* `OHLCVDFAccessor` -> `pd.DataFrame.vbt.ohlc.*`
* `OHLCVDFAccessor` -> `pd.DataFrame.vbt.ohlcv.*`

The accessors inherit `vectorbt.generic.accessors`.

!!! note
    Accessors do not utilize caching."""

import numpy as np
import plotly.graph_objects as go

from vectorbt import _typing as tp
from vectorbt.root_accessors import register_dataframe_vbt_accessor
from vectorbt.utils import checks
from vectorbt.utils.figure import make_figure, make_subplots
from vectorbt.utils.config import merge_dicts
from vectorbt.generic.accessors import GenericDFAccessor


@register_dataframe_vbt_accessor('ohlc')
@register_dataframe_vbt_accessor('ohlcv')
class OHLCVDFAccessor(GenericDFAccessor):  # pragma: no cover
    """Accessor on top of OHLCV data. For DataFrames only.

    Accessible through `pd.DataFrame.vbt.ohlcv`."""

    def __init__(self, obj: tp.Frame, column_names: tp.Optional[tp.Dict[str, str]] = None, **kwargs) -> None:
        self._column_names = column_names

        GenericDFAccessor.__init__(self, obj, column_names=column_names, **kwargs)

    @property
    def column_names(self):
        """Column names."""
        return self._column_names

    def plot(self,
             plot_type: tp.Union[None, str, tp.BaseTraceType] = None,
             display_volume: tp.Optional[bool] = None,
             ohlc_kwargs: tp.KwargsLike = None,
             volume_kwargs: tp.KwargsLike = None,
             ohlc_add_trace_kwargs: tp.KwargsLike = None,
             volume_add_trace_kwargs: tp.KwargsLike = None,
             fig: tp.Optional[tp.BaseFigure] = None,
             **layout_kwargs) -> tp.BaseFigure:
        """Plot OHLCV data.

        Args:
            plot_type: Either 'OHLC', 'Candlestick' or Plotly trace.

                Pass None to use the default.
            display_volume (bool): If True, displays volume as bar chart.
            ohlc_kwargs (dict): Keyword arguments passed to `plot_type`.
            volume_kwargs (dict): Keyword arguments passed to `plotly.graph_objects.Bar`.
            ohlc_add_trace_kwargs (dict): Keyword arguments passed to `add_trace` for OHLC.
            volume_add_trace_kwargs (dict): Keyword arguments passed to `add_trace` for volume.
            fig (Figure or FigureWidget): Figure to add traces to.
            **layout_kwargs: Keyword arguments for layout.

        ## Example

        ```python-repl
        >>> import vectorbt as vbt

        >>> vbt.YFData.download("BTC-USD").get().vbt.ohlcv.plot()
        ```

        ![](/docs/img/ohlcv.svg)
        """
        from vectorbt._settings import settings
        ohlcv_cfg = settings['ohlcv']
        plotting_cfg = settings['plotting']

        column_names = ohlcv_cfg['column_names'] if self.column_names is None else self.column_names
        df_column_names = self.obj.columns.str.lower().tolist()

        if ohlc_kwargs is None:
            ohlc_kwargs = {}
        if volume_kwargs is None:
            volume_kwargs = {}
        if ohlc_add_trace_kwargs is None:
            ohlc_add_trace_kwargs = {}
        if volume_add_trace_kwargs is None:
            volume_add_trace_kwargs = {}
        if display_volume is None:
            display_volume = column_names['volume'].lower() in df_column_names
        if display_volume:
            ohlc_add_trace_kwargs = merge_dicts(dict(row=1, col=1), ohlc_add_trace_kwargs)
            volume_add_trace_kwargs = merge_dicts(dict(row=2, col=1), volume_add_trace_kwargs)

        open = self.obj.iloc[:, df_column_names.index(column_names['open'].lower())]
        high = self.obj.iloc[:, df_column_names.index(column_names['high'].lower())]
        low = self.obj.iloc[:, df_column_names.index(column_names['low'].lower())]
        close = self.obj.iloc[:, df_column_names.index(column_names['close'].lower())]

        # Set up figure
        if fig is None:
            if display_volume:
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0, row_heights=[0.7, 0.3])
            else:
                fig = make_figure()
            fig.update_layout(
                showlegend=True,
                xaxis=dict(
                    rangeslider_visible=False,
                    showgrid=True
                ),
                yaxis=dict(
                    showgrid=True
                )
            )
            if display_volume:
                fig.update_layout(
                    xaxis2=dict(
                        showgrid=True
                    ),
                    yaxis2=dict(
                        showgrid=True
                    ),
                    bargap=0
                )
        fig.update_layout(**layout_kwargs)
        if plot_type is None:
            plot_type = ohlcv_cfg['plot_type']
        if isinstance(plot_type, str):
            if plot_type.lower() == 'ohlc':
                plot_type = 'OHLC'
                plot_obj = go.Ohlc
            elif plot_type.lower() == 'candlestick':
                plot_type = 'Candlestick'
                plot_obj = go.Candlestick
            else:
                raise ValueError("Plot type can be either 'OHLC' or 'Candlestick'")
        else:
            plot_obj = plot_type
        ohlc = plot_obj(
            x=self.wrapper.index,
            open=open,
            high=high,
            low=low,
            close=close,
            name=plot_type,
            increasing=dict(
                line=dict(
                    color=plotting_cfg['color_schema']['increasing']
                )
            ),
            decreasing=dict(
                line=dict(
                    color=plotting_cfg['color_schema']['decreasing']
                )
            )
        )
        ohlc.update(**ohlc_kwargs)
        fig.add_trace(ohlc, **ohlc_add_trace_kwargs)

        if display_volume:
            volume = self.obj.iloc[:, df_column_names.index(column_names['volume'].lower())]

            marker_colors = np.empty(volume.shape, dtype=object)
            marker_colors[(close.values - open.values) > 0] = plotting_cfg['color_schema']['increasing']
            marker_colors[(close.values - open.values) == 0] = plotting_cfg['color_schema']['gray']
            marker_colors[(close.values - open.values) < 0] = plotting_cfg['color_schema']['decreasing']
            volume_bar = go.Bar(
                x=self.wrapper.index,
                y=volume,
                marker=dict(
                    color=marker_colors,
                    line_width=0
                ),
                opacity=0.5,
                name='Volume'
            )
            volume_bar.update(**volume_kwargs)
            fig.add_trace(volume_bar, **volume_add_trace_kwargs)

        return fig
