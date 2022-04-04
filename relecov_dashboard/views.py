from django.shortcuts import render
from plotly.offline import plot
import plotly.graph_objects as go


def index(request):

    return render(request, "relecov_dashboard/index.html")


def index2(request):
    return render(request, "relecov_dashboard/index2.html")


def index3(request):
    def scatter():
        x1 = [1, 2, 3, 4]
        y1 = [30, 35, 25, 45]

        trace = go.Scatter(x=x1, y=y1)
        layout = dict(
            title="Simple Graph",
            xaxis=dict(range=[min(x1), max(x1)]),
            yaxis=dict(range=[min(y1), max(y1)]),
        )

        fig = go.Figure(data=[trace], layout=layout)
        plot_div = plot(fig, output_type="div", include_plotlyjs=False)
        return plot_div

    context = {"plot1": scatter()}

    return render(request, "relecov_dashboard/index3.html", context)
