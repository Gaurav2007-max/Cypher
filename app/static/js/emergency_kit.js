document.addEventListener('DOMContentLoaded', () => {
    const button = document.getElementById('downloadEmergencyKit');
    const status = document.getElementById('emergencyKitStatus');
    if (!button || !status) return;

    const escapeHtml = value => String(value).replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);

    const createOfflineHtml = kit => {
        const embeddedData = JSON.stringify(kit)
            .replace(/</g, '\\u003c')
            .replace(/>/g, '\\u003e')
            .replace(/&/g, '\\u0026');
        const title = escapeHtml(`${kit.city.name} Offline Emergency Kit`);

        return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6f1;color:#20251d;font:16px/1.5 system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:24px}h1,h2{line-height:1.2}h1{margin:0 0 8px}h2{font-size:1.15rem}
.muted{color:#596255}.panel{background:#fff;border:1px solid #dfe5da;border-radius:14px;padding:18px;margin:16px 0}
.warning{border-left:5px solid #bd3428;background:#fff2ef}.warning strong{color:#a12720}
#map{display:block;width:100%;height:auto;max-height:70vh;background:#f7f8f5;border:1px solid #dfe5da;border-radius:10px}
.road{fill:none;stroke:#c3cabe;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.road-major{stroke:#8d9b83;stroke-width:2.7}.facility{stroke:#fff;stroke-width:2}
.legend{display:flex;flex-wrap:wrap;gap:12px 20px;font-size:.9rem}.dot{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px}
ul{padding-left:22px}li{margin:9px 0}.phone{white-space:nowrap}footer{font-size:.85rem}
@media print{body{background:#fff}main{max-width:none;padding:0}.panel{break-inside:avoid}#map{max-height:none}}
</style>
</head>
<body>
<main>
<h1>${title}</h1>
<p class="muted" id="kitMeta"></p>
<section class="panel warning">
<h2>Emergency contact</h2>
<div id="emergencyNumbers"></div>
<p class="muted" id="emergencyNumberNote"></p>
</section>
<section class="panel">
<h2>Offline map — roads and nearby listed facilities</h2>
<div class="legend">
<span><i class="dot" style="background:#315c9b"></i>Police</span>
<span><i class="dot" style="background:#bd3428"></i>Hospital / clinic / doctor</span>
<span><i class="dot" style="background:#d17a16"></i>Petrol pump / fuel</span>
<span><i class="dot" style="background:#744a9d"></i>Fire station</span>
</div>
<svg id="map" viewBox="0 0 1000 700" role="img" aria-label="Offline OpenStreetMap road and facility map">
<defs><clipPath id="mapClip"><rect x="30" y="30" width="940" height="640" rx="8"/></clipPath></defs>
<g id="roadLayer" clip-path="url(#mapClip)"></g><g id="facilityLayer" clip-path="url(#mapClip)"></g>
</svg>
<p class="muted" id="mapStatus"></p>
<div class="warning panel"><strong>Safe/avoid areas:</strong> No authority-verified safe or avoid zones are available for this city. This map does not classify any location as safe or dangerous.</div>
</section>
<section class="panel">
<h2>Facilities in the map area</h2>
<p class="muted">OpenStreetMap entries are community-maintained and may be incomplete, closed, or incorrectly located. Confirm availability before relying on a facility.</p>
<ul id="facilityList"></ul>
</section>
<footer class="panel muted" id="attribution"></footer>
</main>
<script>
const kit = ${embeddedData};
const html = value => String(value).replace(/[&<>"']/g, character => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
})[character]);
const generated = new Date(kit.generated_at);
document.getElementById('kitMeta').textContent =
  'Generated ' + generated.toLocaleString() + ' · ' + kit.city.state + ', ' + kit.city.country +
  ' · OpenStreetMap data within approximately ' + (kit.radius_meters / 1000) + ' km of the city centre.';
document.getElementById('attribution').textContent =
  kit.attribution + ' Facility and road data was retrieved on ' + generated.toISOString() +
  '. This downloaded file works without network access; map tiles are not included or needed.';
const numberBox = document.getElementById('emergencyNumbers');
if (kit.emergency_numbers.length) {
  document.getElementById('emergencyNumberNote').textContent =
    'City/state-specific helplines have not been verified. This is the national number for India, not a city hotline.';
  numberBox.innerHTML = kit.emergency_numbers.map(item =>
    '<p><a class="phone" href="tel:' + html(item.number) + '"><strong>' + html(item.number) +
    '</strong></a> — ' + html(item.label) + ' (' + html(item.scope) + ')</p>'
  ).join('');
} else {
  numberBox.textContent = 'No verified national emergency number is configured for this country.';
  document.getElementById('emergencyNumberNote').textContent =
    'City/state-specific helplines have not been verified. Confirm the local emergency number before travel.';
}
const map = document.getElementById('map');
const center = kit.city;
const scale = 300 / kit.radius_meters;
const longitudeScale = Math.cos(center.latitude * Math.PI / 180);
const project = (latitude, longitude) => ({
  x: 500 + (longitude - center.longitude) * 111320 * longitudeScale * scale,
  y: 350 - (latitude - center.latitude) * 111320 * scale
});
const roadLayer = document.getElementById('roadLayer');
roadLayer.innerHTML = kit.roads.map(road => {
  const points = road.coordinates.map(point => project(point[0], point[1]))
    .map(point => point.x.toFixed(1) + ',' + point.y.toFixed(1)).join(' ');
  const major = ['motorway','trunk','primary','secondary'].includes(road.type) ? ' road-major' : '';
  return '<polyline class="road' + major + '" points="' + points + '"></polyline>';
}).join('');
const colors = {
  police:'#315c9b', hospital:'#bd3428', clinic:'#bd3428', doctors:'#bd3428',
  fuel:'#d17a16', fire_station:'#744a9d'
};
document.getElementById('facilityLayer').innerHTML = kit.facilities.map(place => {
  const point = project(place.latitude, place.longitude);
  return '<circle class="facility" cx="' + point.x.toFixed(1) + '" cy="' + point.y.toFixed(1) +
    '" r="7" fill="' + (colors[place.category] || '#52634b') + '"><title>' +
    html(place.name) + ' — ' + html(place.category_label) + '</title></circle>';
}).join('');
const facilityList = document.getElementById('facilityList');
if (kit.facilities.length) {
  facilityList.innerHTML = kit.facilities.map(place => {
    const details = [place.category_label, place.address, place.phone ? 'Phone: ' + place.phone : '']
      .filter(Boolean).map(html).join(' · ');
    return '<li><strong>' + html(place.name) + '</strong><br><span class="muted">' +
      details + '</span></li>';
  }).join('');
} else {
  facilityList.innerHTML = '<li>No matching facility points were returned for this area.</li>';
}
document.getElementById('mapStatus').textContent = kit.facilities.length
  ? kit.facilities.length + ' facility points and ' + kit.roads.length + ' road segments included.'
  : 'No matching facilities were returned. Road map data may still be available.';
if (!kit.roads.length) {
  document.getElementById('mapStatus').textContent += ' No road segments were returned.';
}
const centerPoint = project(center.latitude, center.longitude);
const centerMarker = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
centerMarker.setAttribute('cx', centerPoint.x);
centerMarker.setAttribute('cy', centerPoint.y);
centerMarker.setAttribute('r', '5');
centerMarker.setAttribute('fill', '#20251d');
centerMarker.innerHTML = '<title>Approximate city centre</title>';
map.appendChild(centerMarker);
</script>
</body>
</html>`;
    };

    button.addEventListener('click', async () => {
        button.disabled = true;
        status.className = 'small mt-3 text-muted';
        status.textContent = 'Retrieving city map and facility data. This requires an internet connection...';
        try {
            const response = await fetch(`/api/safety/emergency-kit/${encodeURIComponent(button.dataset.cityId)}`);
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || 'Could not create the emergency kit.');
            }

            const file = new Blob([createOfflineHtml(result)], { type: 'text/html;charset=utf-8' });
            const objectUrl = URL.createObjectURL(file);
            const link = document.createElement('a');
            const filename = `${button.dataset.cityName || 'city'}-offline-emergency-kit`
                .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
            link.href = objectUrl;
            link.download = `${filename || 'offline-emergency-kit'}.html`;
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
            status.className = 'small mt-3 text-success';
            status.textContent = 'Your standalone offline kit was downloaded. Save it on your device before you lose connectivity.';
        } catch (error) {
            console.error('Could not download the offline emergency kit:', error);
            status.className = 'small mt-3 text-danger';
            status.textContent = error.message || 'Could not download the emergency kit. Connect to the internet and try again.';
        } finally {
            button.disabled = false;
        }
    });
});
