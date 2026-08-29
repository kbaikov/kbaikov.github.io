# Weight

 <script src="https://cdn.plot.ly/plotly-latest.min.js">
 </script>

<div id="container"> </div>

<script>

    var xField = 'date';
    var yField = 'weight';

    var selectorOptions = {
        buttons: [{
            step: 'month',
            stepmode: 'backward',
            count: 1,
            label: '1m'
        }, {
            step: 'month',
            stepmode: 'backward',
            count: 6,
            label: '6m'
        }, {
            step: 'year',
            stepmode: 'todate',
            count: 1,
            label: 'YTD'
        }, {
            step: 'year',
            stepmode: 'backward',
            count: 1,
            label: '1y'
        }, {
            step: 'all',
        }],
    };

    Plotly.d3.csv("result.csv", function (err, rows) {
        if (err) throw err;

        function unpack(rows, key) {
            return rows.map(row => row[key]);
        }

        // Sort rows by date in descending order
        rows.sort((a, b) => new Date(b.date) - new Date(a.date));

        var headerValues = Plotly.d3.keys(rows[0]);
        var cellValues = headerValues.map(header => unpack(rows, header));

        var table = {
            type: 'table',
            columnwidth: Array(headerValues.length).fill(200),
            columnorder: headerValues.map((_, i) => i),
            header: {
                values: headerValues,
                align: "center",
            },
            cells: {
                values: cellValues,
                align: "center",
            },
            domain: { x: [0, 1], y: [0, 0.5] }
        };

        var trace1 = {
            x: unpack(rows, 'date'),
            y: unpack(rows, 'weight'),
            mode: 'lines',
            name: 'Weight',
            connectgaps: true
        };

        var data = [table, trace1];

        var layout = {
            title: "Weight",
            height: 1000,
            xaxis: {
                domain: [0, 1],
                rangeselector: selectorOptions,
                showline: true,
                zeroline: false,
                showgrid: true,
                mirror: true,
                ticklen: 9,
                autorange: true
            },
            yaxis: {
                domain: [0.60, 0.98],
                showgrid: true,
                showline: true,
                gridcolor: '#bdbdbd',
                gridwidth: 1,
                showline: true,
                zeroline: false,
                showgrid: true,
                mirror: true,
                ticklen: 9,
                autorange: true
            }
        };

        Plotly.plot('container', data, layout);
    });


</script>
