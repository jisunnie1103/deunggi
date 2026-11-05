// Offline UI-logic regression: generated cross-province fixtures stay inside this test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/molit_apt_trade_seoul_202610.json')));
const example={...data.districts[0].trades[0],lawd_cd:'26110',apartment_name:'TEST ONLY',deal_date:'2026-10-01',price_krw:400000000};
data.districts.push({lawd_cd:'26110',province:'부산광역시',district:'중구',full_name:'부산광역시 중구',collection_status:'complete',trades:[example]});
data.districts.push({lawd_cd:'26140',province:'부산광역시',district:'서구',full_name:'부산광역시 서구',collection_status:'failed',trades:[]});
const els={},listeners={};
const el=id=>els[id]??={id,value:({province:'capital',region:'all',area:'all',basis:'valid',month:'2026-10'})[id]||'',hidden:id==='monthCalendar',innerHTML:'',textContent:'',classList:{toggle(){}},setAttribute(k,v){this[k]=v},getAttribute(k){return this[k]},removeAttribute(k){delete this[k]},addEventListener(){},querySelector(){return {focus(){}}},focus(){}};
let requested=0,success,failure,flights=[],mapOptions,fitBounds,layerCount=0;
const map={fitBounds(b){fitBounds=b},latLngToContainerPoint:()=>({x:500,y:500}),getCenter:()=>[37.5,127],getZoom:()=>9,setView(){},flyTo(...args){flights.push(args)},remove(){},hasLayer:()=>true,removeLayer(){}};
const layer=()=>({addTo(){layerCount++;return this},on(){return this},bindTooltip(){return this}});
const L={map(_el,options){mapOptions=options;return map},control:Object.assign(()=>({}),{zoom:layer}),tileLayer:layer,divIcon:o=>o,marker:layer,circle:layer,circleMarker:layer};
const context={console,Intl,Date,Math,Set,Map,Number,String,Array,Boolean,Promise,setTimeout,requestAnimationFrame:fn=>fn(),L,navigator:{geolocation:{getCurrentPosition(ok,bad){requested++;success=ok;failure=bad}}},location:{hash:'#dashboard',protocol:'http:'},document:{getElementById:el,querySelector:()=>el('locationButton'),querySelectorAll:()=>[],addEventListener:(type,fn)=>(listeners[type]??=[]).push(fn)},window:{innerWidth:1440,isSecureContext:true,L,DEUNGGI_PREVIEW_DATA:data,addEventListener(){},scrollTo(){}}};
vm.createContext(context);
let source=fs.readFileSync(path.join(root,'assets/dashboard.js'),'utf8').replace('load();\n})();','window.test={route,raw,priced,chooseRegion,syncRegions,scopeHasData,locateMe,setInsights,coverageText,fitScope};load();\n})();');
vm.runInContext(source,context);
setImmediate(()=>{
 const t=context.window.test;
 assert.equal(el('province').value,'capital');assert(mapOptions.scrollWheelZoom&&mapOptions.dragging);assert.equal(mapOptions.minZoom,5);assert.equal(fitBounds[0][0],36.90);
 assert.equal(requested,0,'Location permission must never be requested automatically');
 assert(t.raw().every(r=>r.lawd_cd.startsWith('11')));
 el('province').value='26';el('region').value='all';t.syncRegions();t.route();assert.equal(t.raw().length,1);assert(el('content').innerHTML.includes('부산광역시 전체'));
 el('region').value='26140';t.route();assert.equal(t.scopeHasData(),false);assert(el('content').innerHTML.includes('자료 미수집'));assert(!el('content').innerHTML.includes('share-gauge'));
 el('province').value='all';el('region').value='all';t.route();const nationwideCount=t.raw().length;assert(nationwideCount>1);assert(t.coverageText().includes('미수집'));
 t.chooseRegion('11680');assert.equal(t.raw().every(r=>r.lawd_cd==='11680'),true);assert.equal(el('insightsToggle')['aria-expanded'],'true');
 t.locateMe();t.locateMe();assert.equal(requested,1,'Avoid duplicate pending location requests');success({coords:{latitude:35.18,longitude:129.07,accuracy:25}});assert.equal(flights.at(-1)[0][0],35.18);assert.equal(flights.at(-1)[1],13);assert.equal(el('locationButton').disabled,false);assert(el('mapMessage').textContent.includes('현재 위치로 이동'));
 t.locateMe();failure({code:1});assert(el('mapMessage').textContent.includes('거부'));assert.equal(el('locationButton').disabled,false);
 context.window.isSecureContext=false;t.locateMe();assert(el('mapMessage').textContent.includes('HTTPS'));assert.equal(requested,2);context.window.isSecureContext=true;
 for(const page of ['prices','volume','status','compare','trades','about']){context.location.hash='#'+page;t.route();assert(el('content').innerHTML.length>200,page);}
 console.log('PASS: national/province/county scoping, missing-vs-zero, seven routes, drawer, capital bounds, wheel/drag, opt-in location success/denial/secure-context handling.');
});
