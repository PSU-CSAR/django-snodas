let HIGHLIGHT_LAYERNAME = 'highlight';
let CLICKED_LAYERNAME = 'click_highlight';


function zfill(num, size) {
    var s = num+"";
    while (s.length < size) s = "0" + s;
    return s;
}


// get the pourpoint points for reference
function getPourpoints(callback) {
    $.ajax({
        'type': 'GET',
        'url': 'https://api.snodas.geog.pdx.edu/pourpoints/',
        'datatype': 'json',
        'success': function(result) {
            callback(result);
        }
    });
}

// get the snodas dates
function getSNODASdates(callback) {
    $.ajax({
        'type': 'GET',
        'url': 'https://api.snodas.geog.pdx.edu/tiles/',
        'datatype': 'json',
        'success': function(result) {
            var years = {};
            for (var i = 0; i < result.length; i++) {
                var split = result[i].split('-');
                var year = parseInt(split[0]), month = parseInt(split[1]), day = parseInt(split[2]);
                if (!years[year]) {
                    years[year] = {};
                }
                if (years[year][month]) {
                    years[year][month].push(day);
                } else {
                    years[year][month] = [day];
                }
            }
            callback(years);
        },
    });
}

var map, featureList, snodas_dates, selected_properties;
var date_range_low, date_range_high, doy_start, doy_end, doy_date;

function fmtDate(date, sep) {
    if (!date) {
        return null;
    }

    if (!sep) {
        sep = ''
    }

    var day = date.getDate(), month = date.getMonth() + 1;
    return date.getFullYear() +
        sep +
        (month > 9 ? '' : '0') + month +
        sep +
        (day > 9 ? '' : '0') + day;
}

function month_name_to_num(name) {
    return {
        'JANUARY': 1,
        'FEBRUARY': 2,
        'MARCH': 3,
        'APRIL': 4,
        'MAY': 5,
        'JUNE': 6,
        'JULY': 7,
        'AUGUST': 8,
        'SEPTEMBER': 9,
        'OCTOBER': 10,
        'NOVEMBER': 11,
        'DECEMBER': 12
    }[name.toUpperCase()]
}


//---------------------------------------


class SnodasQuerySelector {
    constructor() {
        this.selected_query = null;
        this.queries = []
        this.menu_id = 'query-selector-menu';
        this.label_id = 'query-label';
        this.form_id = 'snodas-query';

        var parent_id = 'query-container';

        // seems a little silly to build DOM like this?
        var parent = document.getElementById(parent_id);

        var dropdown = document.createElement('DIV');
        dropdown.classList.add('dropdown');
        dropdown.id = 'query-selector';
        var button = document.createElement('BUTTON');
        button.classList.add('btn');
        button.classList.add('btn-primary');
        button.classList.add('dropdown-toggle');
        button.setAttribute('type', 'button');
        button.id = 'query-selector-label';
        button.setAttribute('data-toggle', 'dropdown');
        button.setAttribute('aria-haspopup', 'true');
        button.setAttribute('aria-expanded', 'false');
        button.innerText = 'SNODAS Statistics Query';
        var dropdown_menu = document.createElement('DIV');
        dropdown_menu.classList.add('dropdown-menu');
        dropdown_menu.id = this.menu_id;
        dropdown_menu.setAttribute('aria-labelledby', 'query-selector-label')
        dropdown.appendChild(button);
        dropdown.appendChild(dropdown_menu);

        var label = document.createElement('LABEL');
        label.classList.add('form-label');
        label.setAttribute('for', this.form_id);
        label.id = this.label_id;

        parent.insertBefore(label, parent.childNodes[0]);
        parent.insertBefore(dropdown, parent.childNodes[0]);

        this.clear_selection();
    }

    get_menu_element() {
        return document.getElementById(this.menu_id);
    }

    add_query(label, html, initiator, validator, requestor) {
        var query = new SnodasQuery(label, html, initiator, validator, requestor, this);
        this.get_menu_element().appendChild(query.element);
        this.queries.push(query);
    }

    set_label() {
        var label_txt = 'Choose Query Type';
        if (this.selected_query !== null) {
            label_txt = this.selected_query.label;
        }
        document.getElementById(this.label_id).innerText = label_txt;
    }

    set_form() {
        var form_html = null;
        if (this.selected_query !== null) {
            form_html = this.selected_query.html;
        }
        document.getElementById(this.form_id).innerHTML = form_html;
    }

    clear_selection() {
        this.selected_query = null;
        this.set_label();
        this.set_form();
    }

    validate() {
        if (this.selected_query !== null) {
            this.selected_query.validate();
        }
    }

    request() {
        if (this.selected_query !== null) {
            this.selected_query.request();
        }
    }

    select_query_by_element(query_element) {
        for (var i = 0; i < this.queries.length; i++) {
            if (query_element === this.queries[i].element) {
                if (this.selected_query === this.queries[i]) {
                    return;
                }
                this.selected_query = this.queries[i];
                break;
            }
        }

        if (this.selected_query !== null) {
            this.set_label();
            this.set_form();
            this.selected_query.initiate();
        } else {
            console.log("no match");
        }
    }
}

class SnodasQuery {
    constructor(label, html, initiator, validator, requestor, query_selector) {
        this.label = label;
        this.html = html;
        this.initiator = initiator;
        this.validator = validator;
        this.requestor = requestor;

        this.element = document.createElement('BUTTON');
        this.element.innerText = this.label;
        this.element.setAttribute('type', 'button');
        this.element.classList.add('dropdown-item');
        this.element.onclick = query_selector.onclick;
    }

    initiate() {
        this.initiator();
        this.validator();
    }

    validate() {
        this.validator();
    }

    request() {
        this.requestor();
    }
}

query_selector = new SnodasQuerySelector();
query_selector.onclick = function(event) {
    query_selector.select_query_by_element(event.target);
}

var pp_table_html = '<table class="table table-borderless mb-3 border" id="snodas-pourpoint-table"><tbody><tr><th scope="row">AWDB ID</th><td id="snodas-pourpoint-awdb-id"></td></tr><tr><th scope="row">Name</th><td id="snodas-pourpoint-name"></td></tr></tbody></table>';
var date_html = 'Query Date Range<div class="input-group input-daterange mb-3" id="snodas-range-query-date"><input type="text" class="input-sm form-control" id="snodas-range-query-start" name="start"><div class="input-group-prepend input-group-append"><div class="input-group-text">to</div></div><input type="text" class="input-sm form-control" id="snodas-range-query-end" name="end"></div>';
var doy_html = 'Query Date<div id="snodas-doy-query"><div class="input-group input-daterange mb-3" id="snodas-doy-query-doy"><input type="text" class="input-sm form-control" id="snodas-doy-query-doy1" name="start"></div><select class="form-control" id="snodas-doy-query-years-start"></select>to<select class="form-control" id="snodas-doy-query-years-end"></select></div>';
var variables_html = 'SNODAS Variable:<select class="form-control" id="snodas-query-variable"><option value="depth">Snow Depth</option><option value="swe" selected>Snow Water Equivalent</option><option value="runoff">Runoff</option><option value="sublimation">Sublimation</option><option value="sublimation_blowing">Sublimation (Blowing)</option><option value="precip_solid">Precipitation (Solid)</option><option value="precip_liquid">Precipitation (Liquid)</option><option value="average_temp">Average Temperature</option></select>';
var regression = 'Forecast period:<select class="form-control" id="snodas-query-month-start"><option value="1">January</option><option value="2">February</option><option value="3">March</option><option value="4" selected>April</option><option value="5">May</option><option value="6">June</option><option value="7">July</option><option value="8">August</option><option value="9">September</option><option value="10">October</option><option value="11">November</option><option value="12">December</option></select>to<select class="form-control" id="snodas-query-month-end"><option value="1">January</option><option value="2">February</option><option value="3">March</option><option value="4">April</option><option value="5">May</option><option value="6">June</option><option value="7" selected>July</option><option value="8">August</option><option value="9">September</option><option value="10">October</option><option value="11">November</option><option value="12">December</option></select>';
var submit = '<a url="https://api.snodas.geog.pdx.edu/" role="button" class="btn btn-success disabled" id="snodas-query-btn" aria-disabled="true">Submit Query</a>';

function pp_table_init() {
    if (selected_properties) {
        setPourpointName(selected_properties);
    }
}

query_selector.add_query(
    'SNODAS Values - Date Range',
    pp_table_html + date_html + submit,
    function() {
        pp_table_init();
        date_range_init();
    },
    function() {
        var queryBtn = document.getElementById('snodas-query-btn');
        var pourpointTable = document.getElementById('snodas-pourpoint-table');
        var urlParams = {};

        urlParams['startDate'] = fmtDate($('#snodas-range-query-date').data("datepicker").pickers[0].getDate());
        urlParams['endDate'] = fmtDate($('#snodas-range-query-date').data("datepicker").pickers[1].getDate());
        urlParams['pourpoint_id'] = pourpointTable.getAttribute('pourpoint_id');

        var linkEnd = null;
        if (urlParams.startDate && urlParams.endDate && urlParams.pourpoint_id) {
            linkEnd = 'query/pourpoint/'
                + 'polygon' + '/'
                + urlParams.pourpoint_id + '/'
                + urlParams.startDate + '/'
                + urlParams.endDate + '/';
        }

        if (linkEnd) {
            queryBtn.setAttribute('href', queryBtn.getAttribute('url') + linkEnd);
            L.DomUtil.removeClass(queryBtn, 'disabled');
            queryBtn.setAttribute('aria-disabled', false);
            return true;
        }

        queryBtn.removeAttribute('href');
        L.DomUtil.addClass(queryBtn, 'disabled');
        queryBtn.setAttribute('aria-disabled', true);
        return false;
    },
);

query_selector.add_query(
    'SNODAS Values - Doy Range',
    pp_table_html + doy_html + submit,
    function() {
        // init
        pp_table_init();
        doy_init();
    },
    function() {
        // validate
        var queryBtn = document.getElementById('snodas-query-btn');
        var pourpointTable = document.getElementById('snodas-pourpoint-table');
        var urlParams = {};

        doy = document.getElementById('snodas-doy-query-doy1').value.split(' ');
        urlParams['day'] = doy[0]
        urlParams['month'] = month_name_to_num(doy[1])
        urlParams['startyear'] = document.getElementById('snodas-doy-query-years-start').value;
        urlParams['endyear'] = document.getElementById('snodas-doy-query-years-end').value;
        urlParams['pourpoint_id'] = pourpointTable.getAttribute('pourpoint_id');

        var linkEnd = null;
        if (urlParams.day && urlParams.month && urlParams.startyear && urlParams.endyear && urlParams.pourpoint_id) {
            linkEnd = 'query/pourpoint/'
                + 'polygon' + '/'
                + urlParams.pourpoint_id + '/'
                + zfill(urlParams.month, 2) + '-' + zfill(urlParams.day, 2) + '/'
                + urlParams.startyear + '/'
                + urlParams.endyear + '/';
        }

        if (linkEnd) {
            queryBtn.setAttribute('href', queryBtn.getAttribute('url') + linkEnd);
            L.DomUtil.removeClass(queryBtn, 'disabled');
            queryBtn.setAttribute('aria-disabled', false);
            return true;
        }

        queryBtn.removeAttribute('href');
        L.DomUtil.addClass(queryBtn, 'disabled');
        queryBtn.setAttribute('aria-disabled', true);
        return false;
    },
);

//no netcdf support yet
/*query_selector.add_query(
    'Export NetCDF - Date Range',
    pp_table_html + variables_html + date_html,
);

query_selector.add_query(
    'Export NetCDF - Date Range',
    pp_table_html + variables_html + doy_html,
);*/

query_selector.add_query(
    'SNODAS Streamflow Regression Tool',
    regression + variables_html + doy_html + submit,
    function() {
        // init
        doy_init();
        document.getElementById('snodas-query-month-start').addEventListener('change', function(event) {
            query_selector.validate();
        });
        document.getElementById('snodas-query-month-end').addEventListener('change', function(event) {
            query_selector.validate();
        });
        document.getElementById('snodas-query-variable').addEventListener('change', function(event) {
            query_selector.validate();
        });
    },
    function() {
        // validate
        var queryBtn = document.getElementById('snodas-query-btn');
        var urlParams = {};

        doy = document.getElementById('snodas-doy-query-doy1').value.split(' ');
        urlParams['day'] = doy[0]
        urlParams['month'] = month_name_to_num(doy[1])
        urlParams['startyear'] = document.getElementById('snodas-doy-query-years-start').value;
        urlParams['endyear'] = document.getElementById('snodas-doy-query-years-end').value;
        urlParams['forecaststart'] = document.getElementById('snodas-query-month-start').value;
        urlParams['forecastend'] = document.getElementById('snodas-query-month-end').value;
        urlParams['variable'] = document.getElementById('snodas-query-variable').value;

        var linkEnd = null;
        if (urlParams.day && urlParams.month && urlParams.startyear && urlParams.endyear 
            && urlParams.forecaststart && urlParams.forecastend && urlParams.variable
            && parseInt(urlParams.startyear) <= parseInt(urlParams.endyear)
            && parseInt(urlParams.forecaststart) <= parseInt(urlParams.forecastend)) {
            linkEnd = 'analysis/streamflow/'
                + urlParams.variable + '/'
                + zfill(urlParams.forecaststart, 2) + '/'
                + zfill(urlParams.forecastend, 2) + '/'
                + zfill(urlParams.month, 2) + '-' + zfill(urlParams.day, 2) + '/'
                + urlParams.startyear + '/'
                + urlParams.endyear + '/';
        }

        if (linkEnd) {
            queryBtn.setAttribute('href', queryBtn.getAttribute('url') + linkEnd);
            L.DomUtil.removeClass(queryBtn, 'disabled');
            queryBtn.setAttribute('aria-disabled', false);
            return true;
        }

        queryBtn.removeAttribute('href');
        L.DomUtil.addClass(queryBtn, 'disabled');
        queryBtn.setAttribute('aria-disabled', true);
        return false;
    },
);


function setPourpointName(properties) {
    selected_properties = properties;
    var table = document.getElementById('snodas-pourpoint-table');
    if (table) {
        table.setAttribute('pourpoint_id', properties.pourpoint_id);
        table.setAttribute('is_polygon', properties.is_polygon);
        document.getElementById('snodas-pourpoint-awdb-id').innerText = properties.awdb_id;
        document.getElementById('snodas-pourpoint-name').innerText = properties.name;
        try {
            query_selector.validate();
        } catch {}
    }
}

function clearPourpointName() {
    selected_properties = null;
    var table = document.getElementById('snodas-pourpoint-table');
    if (table) {
        table.removeAttribute('pourpoint_id');
        table.removeAttribute('is_polygon');
        document.getElementById('snodas-pourpoint-awdb-id').innerText = '';
        document.getElementById('snodas-pourpoint-name').innerText = '';
        try {
            query_selector.validate();
        } catch {}
    }
}

getSNODASdates(function(dates) {
    snodas_dates = dates;
    snodas_tile_date_init();
    try {
        date_range_init();
    } catch(err) {}
    try {
        doy_init();
    } catch(err) {}
});

function snodas_tile_date_init() {
    var dates = snodas_dates;
    var max_year = Math.max(...Object.keys(dates));
    var max_month = Math.max(...Object.keys(dates[max_year]));
    var max_day = Math.max(...dates[max_year][max_month]);
    var min_year = Math.min(...Object.keys(dates));
    var min_month = Math.min(...Object.keys(dates[min_year]));
    var min_day = Math.min(...dates[min_year][min_month]);
    var min_date = min_year + (min_month > 9 ? '-' : '-0') + min_month + (min_day > 9 ? '-' : '-0') + min_day;
    var max_date = max_year + (max_month > 9 ? '-' : '-0') + max_month + (max_day > 9 ? '-' : '-0') + max_day;

    $('#snodas-tile-date input').datepicker({
        format: "yyyy-mm-dd",
        startDate: min_date,
        endDate: max_date,
        startView: 0,
        todayBtn: true,
        todayHighlight: true,
        assumeNearbyYear: true,
        maxViewMode: 2,
        zIndexOffset: 1000,
        beforeShowDay: function(date) {
            var months = dates[date.getFullYear()];
            if (months) {
                var days = months[date.getMonth()+1];
                if (days && days.indexOf(date.getDate()) != -1) {
                    return true;
                }
            }
            return false;
        },
        beforeShowMonth: function(date) {
            var months = dates[date.getFullYear()];
            if (months && months[date.getMonth()+1]) {
                return true;
            }
            return false;
        },
        beforeShowYear: function(date) {
            if (dates[date.getFullYear()]) {
                return true;
            }
            return false;
        }
    });
    $('#snodas-tile-date input').datepicker('update', max_date);
    $("#snodas-refresh").click();
}

function date_range_init() {
    var dates = snodas_dates;
    var max_year = Math.max(...Object.keys(dates));
    var max_month = Math.max(...Object.keys(dates[max_year]));
    var max_day = Math.max(...dates[max_year][max_month]);
    var min_year = Math.min(...Object.keys(dates));
    var min_month = Math.min(...Object.keys(dates[min_year]));
    var min_day = Math.min(...dates[min_year][min_month]);
    var min_date = min_year + (min_month > 9 ? '-' : '-0') + min_month + (min_day > 9 ? '-' : '-0') + min_day;
    var max_date = max_year + (max_month > 9 ? '-' : '-0') + max_month + (max_day > 9 ? '-' : '-0') + max_day;

    $('#snodas-range-query-date').datepicker({
        format: "yyyy-mm-dd",
        startDate: min_date,
        endDate: max_date,
        startView: 0,
        todayBtn: true,
        todayHighlight: true,
        assumeNearbyYear: true,
        maxViewMode: 2,
        zIndexOffset: 1000,
    });

    if (!date_range_low) {
        date_range_low = new Date(max_date);
        date_range_low.setDate(date_range_low.getDate() - 6);
    }

    if (!date_range_high) {
        date_range_high = max_date;
    }
    
    $("#snodas-range-query-date").data("datepicker").pickers[1].setDate(date_range_high);
    $("#snodas-range-query-date").data("datepicker").pickers[0].setDate(date_range_low);

    $("#snodas-range-query-date").datepicker().on('changeDate', function(event) {
        date_range_low = document.getElementById('snodas-range-query-start').value;
        date_range_high = document.getElementById('snodas-range-query-end').value;
        query_selector.validate();
    });
}

function doy_init() {
    var dates = snodas_dates;
    var max_year = Math.max(...Object.keys(dates));
    var max_month = Math.max(...Object.keys(dates[max_year]));
    var max_day = Math.max(...dates[max_year][max_month]);
    var min_year = Math.min(...Object.keys(dates));
    var min_month = Math.min(...Object.keys(dates[min_year]));
    var min_day = Math.min(...dates[min_year][min_month]);
    var min_date = min_year + (min_month > 9 ? '-' : '-0') + min_month + (min_day > 9 ? '-' : '-0') + min_day;
    var max_date = max_year + (max_month > 9 ? '-' : '-0') + max_month + (max_day > 9 ? '-' : '-0') + max_day;

    $('#snodas-doy-query-doy').datepicker({
        format: "dd MM",
        assumeNearbyYear: true,
        showWeekDays: false,
        maxViewMode: 1,
        zIndexOffset: 1000,
    });

    if (!doy_date) {
        doy_date = max_date;
    }

    $("#snodas-doy-query-doy").data("datepicker").pickers[0].setDate(doy_date);

    $("#snodas-doy-query-doy").datepicker().on('changeDate', function(event) {
        doy_date = $("#snodas-doy-query-doy").data("datepicker").pickers[0].getDate();
        query_selector.validate();
    });

    var doy_query_years_start = document.getElementById('snodas-doy-query-years-start');
    var doy_query_years_end = document.getElementById('snodas-doy-query-years-end');

    for (var year = min_year; year <= max_year; year++) {
        var option = document.createElement("option");
        option.text = year;
        doy_query_years_start.add(option);

        var option = document.createElement("option");
        option.text = year;
        doy_query_years_end.add(option);
    }

    if (!doy_start) {
        doy_start = min_year;
    }

    if (!doy_end) {
        doy_end = max_year;
    }

    doy_query_years_start.addEventListener('change', function(event) {
        doy_start = doy_query_years_start.value;
        query_selector.validate();
    });
    doy_query_years_end.addEventListener('change', function(event) {
        doy_end = doy_query_years_end.value;
        query_selector.validate();
    });

    doy_query_years_start.value = doy_start;
    doy_query_years_end.value = doy_end;
}

$("#calendar-btn").click(function() {
    $('#snodas-tile-date input').datepicker('show');
});

//
function sizeLayerControl() {
    $(".leaflet-control-layers").css("max-height", $("#map").height() - 50);
}

$(window).resize(function() {
    sizeLayerControl();
});


// show/hide sidebar listeners and functions
$("#sidebar-toggle-btn").click(function() {
    animateSidebar();
    return false;
});

$("#sidebar-hide-btn").click(function() {
    animateSidebar();
    return false;
});

$('#sidebar-show-btn').click(function() {
    animateSidebar();
    return false;
});

function animateSidebar() {
    var sidebar_show_btn = $('#sidebar-show-btn');
    var hidden = false;
    if (!sidebar_show_btn.hasClass('hidden')) {
        sidebar_show_btn.addClass('hidden');
        hidden = true;
    }
    $("#sidebar").animate(
        {width: "toggle"},
        350,
        function() {
            if (!hidden) {
                sidebar_show_btn.removeClass('hidden');
            }
            map.invalidateSize();
        }
    );
}

// Basemap Layers
var cartoLight = L.tileLayer(
    "https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png",
    {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://cartodb.com/attributions">CartoDB</a>'
    }
);
var usgsImagery = L.tileLayer(
    "http://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
    {
        maxZoom: 15,
        attribution: "Aerial Imagery courtesy USGS",
    }
);

// snodas tile layer
var snodasURL = 'https://{s}.snodas.geog.pdx.edu/tiles/{date}/{z}/{x}/{y}.png'
var snodasTiles = L.tileLayer(
    '',
    {
        subdomains: "fghij",
        tms: true,
        maxNativeZoom: 15,
        bounds: [[52.8754, -124.7337], [24.9504, -66.9421]],
    },
);

snodasTiles.setDate = function(date) {
    if (!this._date || this._date !== date) {
        snodasTiles._date = date;
        snodasTiles.setUrl(
            L.Util.template(
                snodasURL,
                {
                    date: fmtDate(date),
                    s: '{s}',
                    z: '{z}',
                    x: '{x}',
                    y: '{y}',
                },
            ),
        );
    }
}

snodasTiles.update = function() {
    var date = $('#snodas-tile-date input').datepicker('getDate');
    snodasTiles.setDate(date)
    if (!map.hasLayer(snodasTiles) && $("#snodas-on").prop("checked")) {
        map.addLayer(snodasTiles);
    } else if (map.hasLayer(snodasTiles) && !$("#snodas-on").prop("checked")) {
        map.removeLayer(snodasTiles);
    }
}

$("#snodas-refresh").click(function(e) {
    //console.log("snodas refresh clicked");
    snodasTiles.update();
});

$("#snodas-on").change(function(e) {
    //console.log("snodas toggle clicked");
    snodasTiles.update();
});

// watershed tile layer
var polygonOptions = {
    fill: false,
    weight: 1,
    color: '#4455FF',
    opacity: 1
}
var polygonSelectedOptions = {
    fill: false,
    weight: 2,
    color: '#223399',
    opacity: 1,
}
var polygonClickedOptions = {
    fill: false,
    weight: 4,
    color: '#BB2244',
    opacity: 1,
}
var polygonClickedSelectedOptions = {
    fill: false,
    weight: 5,
    color: '#BB2244',
    opacity: 1,
}
var vTileOptions = {
    subdomains: "abcde",
    rendererFactory: L.canvas.tile,
    tms: true,
    vectorTileLayerStyles: {
        // A plain set of L.Path options.
        polygons: polygonOptions
    },
    getFeatureId: function(feature) {
        return feature.properties.pourpoint_id;
    },
    interactive: true
};
var watersheds = L.vectorGrid.protobuf(
    'https://{s}.snodas.geog.pdx.edu/pourpoints/{z}/{x}/{y}.mvt',
    vTileOptions
);

watersheds._highlight = null;
watersheds._clicked = null;

watersheds._makeCopyID = function(id, layerName) {
    return layerName + '_' + id;
}

watersheds._clearHighlight = function(layerName) {
    for (var tileKey in this._vectorTiles) {
        var tile = this._vectorTiles[tileKey];
        var features = tile._features;
        for (var fid in features) {
            var data = features[fid];
            if (data && data.layerName === layerName) {
                tile._removePath(data.feature);
                delete features[fid];
            }
        }
    }
}

watersheds.clearHighlight = function() {
    this._clearHighlight(HIGHLIGHT_LAYERNAME);
    this._highlight = null;
}

watersheds.clearClickedHighlight = function() {
    this._clearHighlight(CLICKED_LAYERNAME);
    this._clicked = null;
}

watersheds._copyFeature = function(original, layerName) {
    var copy = Object.create(original);
    copy._parts = JSON.parse(JSON.stringify(original._parts));
    copy.properties = JSON.parse(JSON.stringify(original.properties));
    copy.options = JSON.parse(JSON.stringify(original.options));
    copy.properties.pourpoint_id = this._makeCopyID(copy.properties.pourpoint_id, layerName);
    copy._renderer = original._renderer;
    copy._eventParents = original._eventParents;
    copy.initHooksCalled = true;
    copy._leaflet_id = null;  // unset the duplicate leaflet ID
    L.Util.stamp(copy);       // now give it a unique ID
    return copy;
}

watersheds._addHighlight = function(id, layerName, styleOptions) {
    this._clearHighlight(layerName);
    for (var tileKey in this._vectorTiles) {
        var tile = this._vectorTiles[tileKey];
        var data = tile._features[id];
        if (data) {
            // copy the watershed feature so we can add one with "highlight"
            var feat = this._copyFeature(data.feature, layerName);

            // resolve the style to be applied
            styleOptions = (styleOptions instanceof Function) ?
                styleOptions(feat.properties, tile.getCoord().z) :
                styleOptions;

            if (!(styleOptions instanceof Array)) {
                styleOptions = [styleOptions];
            }

            for (var j = 0; j < styleOptions.length; j++) {
                var style = L.extend({}, L.Path.prototype.options, styleOptions[j]);
                // render the feature with the style,
                // and add it to the tile (renderer)
                feat.render(tile, style);
                tile._addPath(feat);
            }

            // makeInteractive sets the pxBounds
            // but we make sure we can't interact with
            // the feature by specifically setting the
            // interactivity to false
            feat.makeInteractive();
            feat.options.interactive = false;
    
            // add the feature to the tile's list
            // so we can find it again later
            tile._features[feat.properties.pourpoint_id] = {
                layerName: layerName,
                feature: feat
            };
        }
    }
}

watersheds.addHighlight = function(id) {
    var styleOptions = polygonSelectedOptions;
    if (this._clicked && this._clicked === id) {
        styleOptions = polygonClickedSelectedOptions;
    }
    this._addHighlight(id, HIGHLIGHT_LAYERNAME, styleOptions);
    this._highlight = id;
}

watersheds.addClickedSelectedHighlight = function(id) {
    this._addHighlight(id, CLICKED_LAYERNAME, polygonClickedSelectedOptions);
    this._clicked = id;
}

watersheds.addClickedHighlight = function(id) {
    this._addHighlight(id, CLICKED_LAYERNAME, polygonClickedOptions);
    this._clicked = id;
}

watersheds.refresh = function() {
    if (this._highlight) {
        watersheds.addHighlight(this._highlight);
    }
    if (this._clicked && this._clicked !== this._highlight) {
        watersheds.addClickedHighlight(this._clicked);
    } else if (this._clicked) {
        watersheds.addClickedSelectedHighlight(this._clicked);
    }
}

watersheds.hasFeature = function(id) {
    for (var tileKey in watersheds._vectorTiles) {
        var tile = watersheds._vectorTiles[tileKey];
        var data = tile._features[id];
        if (data) {
            return true;
        }
    }
    return false;
}

// create the map, initializing zoom, center, and layers
map = L.map("map", {
    zoom: 4,
    minZoom: 3,
    center: [39.8283, -98.5795],
    layers: [cartoLight, watersheds],
    zoomControl: false,
    attributionControl: false
});

var pointOptions = function(feature) {
    // we don't want to display the pourpoints
    // if we are zoomed too far out
    if (map.getZoom() >= 7) {
        return {
            radius: 8,
            fill: true,
            fillOpacity: 0,
            weight: 1,
            color: '#227722'
        }
    }
    return { weight: 0, fill: false }
}

var pointSelectedOptions = {
    radius: 8,
    fill: true,
    fillOpacity: 100,
    weight: 1,
    color: '#223399',
    fillColor: '#223399'
}
var pointClickedOptions = {
    radius: 8,
    fill: true,
    fillOpacity: 100,
    weight: 1,
    color: '#BB2244',
    fillColor: '#BB2244'
}

var pourpoints = L.geoJson(null, {
    style: pointOptions,
    pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, pointOptions);
    },
    onEachFeature: function (feature, layer) {
        if (feature.properties) {
            layer.on({
                click: function(e) {
                    var properties = feature.properties;
                    // TODO: right now we want to always do polygon queries where possible
                    // as the point queries are not yet supported
                    //properties['is_polygon'] = false;
                    properties['is_polygon'] = watersheds.hasFeature(
                        feature.properties.pourpoint_id
                    );
                    setPourpointName(properties);
                    pourpoints.addClickedHighlight(layer);
                    watersheds.addClickedSelectedHighlight(feature.properties.pourpoint_id);
                    L.DomEvent.stop(e);
                },
                mouseover: function (e) {
                    pourpoints.addHighlight(layer);
                    watersheds.addHighlight(feature.properties.pourpoint_id);
                    L.DomEvent.stop(e);
                },
                mouseout: function (e) {
                    pourpoints.clearHighlight();
                    watersheds.clearHighlight();
                    L.DomEvent.stop(e);
                }
            });
        }
    }
});

pourpoints._highlight = null;
pourpoints._clicked = null;

pourpoints.getLayerByID = function(id) {
    var lyr;
    this.eachLayer(function(layer) {
        if (layer.feature.properties.pourpoint_id == id) {
            lyr = layer;
            return;
        }
    });
    return lyr;
}

pourpoints._addHighlight = function(layer, styleOptions) {
    if (layer) {
        layer.setStyle(styleOptions).bringToFront();
    }
}

pourpoints._clearHighlight = function(layer) {
    if (layer) {
        layer.setStyle(pointOptions(layer));
    }
}

pourpoints.addHighlight = function(layer) {
    if (!layer) { return; }
    this._clearHighlight(this._highlight)

    var styleOptions = pointSelectedOptions;
    if (layer === this._clicked) {
        styleOptions = pointClickedOptions;
    } else {
        this._highlight = layer;
    }
    this._addHighlight(layer, styleOptions);
}

pourpoints.addClickedHighlight = function(layer) {
    if (!layer) { return; }
    this._clearHighlight(this._clicked);
    this._clicked = layer;
    this._addHighlight(layer, pointClickedOptions);
    if (this._highlight === this._clicked) {
        this._highlight = null;
    }
}

pourpoints.clearHighlight = function() {
    if (this._highlight && this._highlight !== this._clicked) {
        this._clearHighlight(this._highlight);
        this._highlight = null;
    }
}

pourpoints.clearClickedHighlight = function() {
    if (this._clicked) {
        this._clearHighlight(this._clicked);
        this._clicked = null;
    }
}

pourpoints.refresh = function() {
    if (map.hasLayer(this)) {
        this.eachLayer(function(lyr) {
            lyr.setStyle(pointOptions(lyr));
        });
        if (this._highlight) {
            this._addHighlight(this._highlight, pointSelectedOptions);
        }
        if (this._clicked) {
            this._addHighlight(this._clicked, pointClickedOptions);
        }
    }
}

getPourpoints(function(data) {
    pourpoints.addData(data['features']);
    pourpoints.addTo(map);
});

watersheds.on('click', function(e) {
    //console.log("click " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name);
    var properties = e.layer.properties;
    properties['is_polygon'] = true;
    setPourpointName(properties);
    pourpoints.addClickedHighlight(pourpoints.getLayerByID(e.layer.properties.pourpoint_id));
    this.addClickedSelectedHighlight(properties.pourpoint_id);
    this._clicked = e.layer.properties.pourpoint_id;
    L.DomEvent.stop(e);
});


watersheds.on('mouseover', function(e) {
    //console.log("mouseover " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name)
    pourpoints.addHighlight(pourpoints.getLayerByID(e.layer.properties.pourpoint_id));
    this.addHighlight(e.layer.properties.pourpoint_id);
});

watersheds.on('mouseout', function(e) {
    //console.log("mouseout " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name)
    pourpoints.clearHighlight();
    this.clearHighlight();
    if (this._clicked && this._clicked === e.layer.properties.pourpoint_id) {
        this.addClickedHighlight(e.layer.properties.pourpoint_id);
    }
});

watersheds.on("load", function(e) {
    watersheds.refresh();
});


function toggleValid(ele, isValid) {
    if (isValid === undefined) {
        L.DomUtil.removeClass(ele, 'is-invalid');
        L.DomUtil.removeClass(ele, 'is-valid');
    } else {
        L.DomUtil.removeClass(ele, isValid ? 'is-invalid' : 'is-valid');
        L.DomUtil.addClass(ele, isValid ? 'is-valid' : 'is-invalid');
    }
}

map.on('zoomend', function(e){
    pourpoints.refresh();
    watersheds.refresh();
});

// Clear feature highlight when map is clicked
map.on('click', function(e) {
    pourpoints.clearClickedHighlight();
    watersheds.clearClickedHighlight();
    clearPourpointName();
});

map.on('baselayerchange', function(e) {
    snodasTiles.bringToFront()
    watersheds.bringToFront()
});

// Attribution control
function updateAttribution(e) {
    $.each(map._layers, function(index, layer) {
        if (layer.getAttribution) {
            var attrib = layer.getAttribution();
            if (attrib) {
                $('#attribution').html(attrib);
            }
        }
    });
}
map.on('layeradd', updateAttribution);
map.on('layerremove', updateAttribution);

var attributionControl = L.control({
    position: 'bottomright',
});
attributionControl.onAdd = function(map) {
    var div = L.DomUtil.create(
        'div',
        'leaflet-control-attribution',
    );
    // TODO: this should be templated externally, perhaps handlebars
    div.innerHTML = "<span class='hidden-xs'>Developed by <a href='https://www.pdx.edu/geography/center-for-spatial-analysis-research-csar'>PSU CSAR</a> | </span><a href='#' onclick='$(\"#attributionModal\").modal(\"show\"); return false;'>Attribution</a>";
    return div;
};
map.addControl(attributionControl);


// zoom in and out buttons
var zoomControl = L.control.zoom({
  position: 'bottomright',
}).addTo(map);


// displayed layer selector
var baseLayers = {
    "Street Map": cartoLight,
    "Aerial Imagery": usgsImagery,
};

var groupedOverlays = {
    "Pour Point Reference": {
        "Watersheds": watersheds,
        "Pour Points": pourpoints
    }
}

var layerControl = L.control.groupedLayers(
    baseLayers,
    groupedOverlays,
    {}
).addTo(map);


// once loading is done:
//   - hide the loading spinner
//   - put the layer control where it needs to be
//   - populate the featureList var for the sidebar
$(document).one("ajaxStop", function() {
    $("#loading").hide();
    sizeLayerControl();
});

// Leaflet patch to make layer control scrollable on touch browsers
var container = $(".leaflet-control-layers")[0];
if (!L.Browser.touch) {
    L.DomEvent
    .disableClickPropagation(container)
    .disableScrollPropagation(container);
} else {
    L.DomEvent.disableClickPropagation(container);
}
