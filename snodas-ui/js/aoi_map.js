// used to store the collection of AOI objects
var aois = {}

// request AOIs boundaries and whatnot from server
function getAOIboundaries(callback) {
    jQuery.ajax({
        'type': 'GET',
        'url': POURPOINT_URL,
        'datatype': 'json',
        'success': function(result) {
            for (var i = 0; i < result['features'].length; i++) {
                var _aois = result['features'][i]['properties']['aois'];
                for (var j = 0; j < _aois.length; j++) {
                    aois[_aois[j].id] = _aois[j];
                }
            }
            callback(result);
        }
    });
}

// get the pourpoint points for reference
function getPourpoints(callback) {
    jQuery.ajax({
        'type': 'GET',
        'url': 'https://snodas.geog.pdx.edu/pourpoints/',
        'datatype': 'json',
        'success': function(result) {
            callback(result);
        }
    });
}

var map, featureList;

//
function sizeLayerControl() {
    $(".leaflet-control-layers").css("max-height", $("#map").height() - 50);
}

$(window).resize(function() {
    sizeLayerControl();
});

// feature list listeners and functions
$("#feature-list").on({
    mouseenter: function (e) {
        var featureRow = this;
        var layer = AOIboundaries.getLayer(
            parseInt($(featureRow).attr("id"), 10)
        );
        addFeatureHighlight(layer);
    },
    mouseleave: function (e) {
        var featureRow = this;
        var layer = AOIboundaries.getLayer(
            parseInt($(featureRow).attr("id"), 10)
        );
        if (!layer.isPopupOpen()) {
            clearHighlight();
        }
    }
}, ".feature-row");

$('#feature-list').on("click", ".pourpoint-header", function(e) {
    // Hide sidebar and go to the map on small screens
    if (document.body.clientWidth <= 767) {
        $("#sidebar").hide();
        map.invalidateSize();
    }
});

$('#feature-list').on('show.bs.collapse', '.feature-row', function(e) {
    var featureRow = this;
    $(featureRow).find(".expand-icon").removeClass('fa-plus-square').addClass('fa-minus-square');
});

$('#feature-list').on('hide.bs.collapse', '.feature-row', function(e) {
    $(this).find(".expand-icon").removeClass('fa-minus-square').addClass('fa-plus-square');
});

$("#clear-btn").click(function() {
    clearFilter();
});

function clearFilter() {
    document.getElementById("filter").value = "";
    featureList.search();
}

$('#feature-list').on('click', '.zoom-to-pp', function(e) {
    var layer = AOIboundaries.getLayer(parseInt($(this).parents().eq(4).attr('id')));
    map.fitBounds(layer.getBounds(), {
        "maxZoom": 9,
        "animate": true,
    });
    return false;
});

$('#feature-list').on('click', '.aoi-row', function(event){
    var aoiRow = this;
    makeAOIModal(aois[$(aoiRow).attr("id")]);
});


var aoiModalTemplate = Handlebars.compile($('#aoimodal-template').html());
function makeAOIModal(aoi_data) {
    $("#aoiModal").html(aoiModalTemplate(aoi_data));
    $("#aoiModal").modal("show");
}

function aoiListClick(id) {
    var layer = AOIboundaries.getLayer(id);
    layer.fire("click");
    // Hide sidebar and go to the map on small screens
    if (document.body.clientWidth <= 767) {
        $("#sidebar").hide();
        map.invalidateSize();
    }
}

var featureRowTemplate = Handlebars.compile($('#featurerow-template').html());
function makeFeatureRow(layer) {
    var context = {
        id: L.stamp(layer),
        featureName: layer.feature.properties.name,
        aois: layer.feature.properties.aois
    };
    return featureRowTemplate(context);
}

function syncSidebar() {
    // Empty sidebar features
    $("#feature-list").empty();
    AOIboundaries.eachLayer(function (layer) {
        $("#feature-list").append(makeFeatureRow(layer));
    });
    // Update list.js featureList
    featureList = new List("features", {
        valueNames: ["feature-name"]
    });
    featureList.sort("feature-name", {
        order: "asc"
    });
    clearFilter();
    $("#loading").hide();
}


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
        attribution: "Aerial Imagery courtesy USGS"
    }
);


// watershed tile layer
var polygonOptions = {
    fill: false,
    weight: 1.5,
    color: '#4455FF',
    opacity: 1
}
var polygonSelectedOptions = {
    fill: false,
    weight: 5,
    color: '#223399',
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

watersheds.clearHighlight = function () {
    for (var tileKey in watersheds._vectorTiles) {
        var tile = watersheds._vectorTiles[tileKey];
        var features = tile._features;
        for (var fid in features) {
            var data = features[fid];
            if (data && data.layerName === 'highlight') {
                tile._removePath(data.feature);
                delete features[fid];
            }
        }
    }
}

watersheds.copyFeature = function (original) {
    var copy = Object.create(original);
    copy._parts = JSON.parse(JSON.stringify(original._parts));
    copy.properties = JSON.parse(JSON.stringify(original.properties));
    copy.options = JSON.parse(JSON.stringify(original.options));
    copy.properties.pourpoint_id = 'cpy_' + copy.properties.pourpoint_id;
    copy._renderer = original._renderer;
    copy._eventParents = original._eventParents;
    copy.initHooksCalled = true;
    copy._leaflet_id = null;  // unset the duplicate leaflet ID
    L.Util.stamp(copy);       // now give it a unique ID
    return copy;
}

watersheds.addHighlight = function (id) {
    watersheds.clearHighlight();
    var styleOptions = polygonSelectedOptions;
    for (var tileKey in watersheds._vectorTiles) {
        var tile = watersheds._vectorTiles[tileKey];
        var data = tile._features[id];
        if (data) {
            // copy the watershed feature so we can add one with "highlight"
            var feat = watersheds.copyFeature(data.feature);

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
                layerName: "highlight",
                feature: feat
            };
        }
    }
}

// AOI Layer
var highlightStyle = {
    fillColor: "#0000b2",
    fillOpacity: "8",
};

var highlight = L.geoJson(null);

function clearHighlight() {
    map.closePopup();
    highlight.clearLayers();
}

function addFeatureHighlight(layer) {
    if (!layer.isPopupOpen()) {
        clearHighlight();
    }
    newLayer = L.geoJson(layer.feature, {style: highlightStyle});
    highlight.clearLayers().addLayer(newLayer);
}

function clearFeatureHighlight(layer) {
    highlight.removeLayer(layer);
}


var defaultStyle = {
    "color": "#b20000",
    "weight": 0,
    "fillOpacity": .75
};


var AOIboundaries = L.geoJson(null, {
    style: defaultStyle,
    onEachFeature: function (feature, layer) {
        if (feature.properties) {
            layer.bindPopup(
                feature.properties.awdb_id + ' ' +
                feature.properties.name
            );
            layer.on({
                click: function (e) {
                    addFeatureHighlight(layer);
                    L.DomEvent.stop(e);
                }
            });
        }
    }
});


// create the map, initializing zoom, center, and layers
map = L.map("map", {
    zoom: 4,
    minZoom: 3,
    center: [39.8283, -98.5795],
    layers: [cartoLight, highlight, watersheds],
    zoomControl: false,
    attributionControl: false
});


getAOIboundaries(function(data) {
    alert('getAOIboundaries');
    AOIboundaries.addData(data);
    map.addLayer(AOIboundaries);
    syncSidebar();
    try {
        map.fitBounds(
            AOIboundaries.getBounds(),
            {"animate": true}
        );
    } catch (e) {
        // pass -- we don't have any AOIs
    }
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

var pourpoints = L.geoJson(null, {
    style: pointOptions,
    pointToLayer: function (feature, latlng) {
        return L.circleMarker(latlng, pointOptions);
    },
    onEachFeature: function (feature, layer) {
        if (feature.properties) {
            layer.bindPopup(
                feature.properties.awdb_id + ' ' +
                feature.properties.name
            );
            layer.on({
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

pourpoints.addHighlight = function (layer) {
    if (this._map) {
        this.clearHighlight();
        layer.setStyle(pointSelectedOptions).bringToFront();
        this._highlight = layer;
    }
}

pourpoints.addHighlightByID = function (id) {
    if (this._map) {
        var layer;
        this.eachLayer(function(lyr) {
            if (lyr.feature.properties.pourpoint_id == id) {
                layer = lyr;
                return;
            }
        });
        this.addHighlight(layer);
    }
}

pourpoints.clearHighlight = function () {
    if (this._map && this._highlight) {
        this._highlight.setStyle(pointOptions(this._highlight));
        this._highlight = null;
    }
}

pourpoints.refresh = function () {
    if (this._map) {
        this.eachLayer(function(lyr) {
            lyr.setStyle(pointOptions(this._highlight));
        });
    }
}

getPourpoints(function(data) {
    pourpoints.addData(data['features']);
    pourpoints.addTo(map);
});

watersheds.on('click', function(e) {
    //console.log("click " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name);
    L.popup()
        .setContent(
            e.layer.properties.awdb_id + ' ' +
            e.layer.properties.name
        )
        .setLatLng(e.latlng)
        .openOn(map);
    L.DomEvent.stop(e);
});


watersheds.on('mouseover', function (e) {
    //console.log("mouseover " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name)
    pourpoints.addHighlightByID(e.layer.properties.pourpoint_id);
    watersheds.addHighlight(e.layer.properties.pourpoint_id);
});

watersheds.on('mouseout', function (e) {
    //console.log("mouseout " + e.layer.properties.pourpoint_id + " " + e.layer.properties.name)
    pourpoints.clearHighlight();
    watersheds.clearHighlight();
});


map.on("zoomend", function(){
    pourpoints.refresh();
});

// Clear feature highlight when map is clicked
map.on("click", function(e) {
    clearHighlight();
});

// Attribution control
function updateAttribution(e) {
    $.each(map._layers, function(index, layer) {
        if (layer.getAttribution) {
            var attrib = layer.getAttribution();
            if (attrib) {
                $("#attribution").html(attrib);
            }
        }
    });
}
map.on("layeradd", updateAttribution);
map.on("layerremove", updateAttribution);

var attributionControl = L.control({
    position: "bottomright"
});
attributionControl.onAdd = function (map) {
    var div = L.DomUtil.create(
        "div",
        "leaflet-control-attribution"
    );
    // TODO: this should be templated externally, perhaps handlebars
    div.innerHTML = "<span class='hidden-xs'>Developed by <a href='https://www.pdx.edu/geography/center-for-spatial-analysis-research-csar'>PSU CSAR</a> | </span><a href='#' onclick='$(\"#attributionModal\").modal(\"show\"); return false;'>Attribution</a>";
    return div;
};
map.addControl(attributionControl);


// zoom in and out buttons
var zoomControl = L.control.zoom({
  position: "bottomright"
}).addTo(map);


// zoom to AOI data extent button
L.Control.ZoomToExtent = L.Control.extend({
    options: {
        position: 'topleft',
        text: '<i class="fa fa-arrows-alt" aria-hidden="true"></i>',
        title: 'Zoom to Data Extent',
        className: 'leaflet-control-zoomtoextent',
        layer: ''
    },
    onAdd: function (map) {
        this._map = map;
        return this._initLayout();
    },
    _initLayout: function () {
        var container = L.DomUtil.create('div', 'leaflet-bar ' +
        this.options.className);
        this._container = container;
        this._fullExtentButton = this._createExtentButton(container);
        L.DomEvent.disableClickPropagation(container);
        return this._container;
    },
    _createExtentButton: function () {
        var link = L.DomUtil.create(
            'a',
            this.options.className + '-toggle',
            this._container
        );
        link.href = '#';
        link.innerHTML = this.options.text;
        link.title = this.options.title;
        L.DomEvent
            .on(link, 'mousedown dblclick', L.DomEvent.stopPropagation)
            .on(link, 'click', L.DomEvent.stop)
            .on(link, 'click', this._zoomToDefault, this);
        return link;
    },
    _zoomToDefault: function () {
        this._map.fitBounds(this.options.layer.getBounds());
    }
});

L.Map.addInitHook(function () {
    if (this.options.zoomToExtentControl) {
        this.addControl(new L.Control.ZoomToExtent());
    }
});

L.control.zoomToExtent = function (options) {
    return new L.Control.ZoomToExtent(options);
};

var zoomToExtentControl = L.control.zoomToExtent({
    position: "bottomright",
    layer: AOIboundaries,
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
$(document).one("ajaxStop", function () {
    $("#loading").hide();
    sizeLayerControl();
    featureList = new List(
        "features",
        {valueNames: ["feature-name"]}
    );
    featureList.sort(
        "feature-name",
        {order: "asc"}
    );
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
