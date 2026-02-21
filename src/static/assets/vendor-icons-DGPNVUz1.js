import{h as d}from"./vendor-6RIulmtG.js";/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M=c=>{for(const e in c)if(e.startsWith("aria-")||e==="role"||e==="title")return!0;return!1};/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const p=c=>c==="";/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const m=(...c)=>c.filter((e,h,t)=>!!e&&e.trim()!==""&&t.indexOf(e)===h).join(" ").trim();/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const o=c=>c.replace(/([a-z0-9])([A-Z])/g,"$1-$2").toLowerCase();/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const x=c=>c.replace(/^([A-Z])|[\s-_]+(\w)/g,(e,h,t)=>t?t.toUpperCase():h.toLowerCase());/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const z=c=>{const e=x(c);return e.charAt(0).toUpperCase()+e.slice(1)};/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */var l={xmlns:"http://www.w3.org/2000/svg",width:24,height:24,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor","stroke-width":2,"stroke-linecap":"round","stroke-linejoin":"round"};/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const g=({name:c,iconNode:e,absoluteStrokeWidth:h,"absolute-stroke-width":t,strokeWidth:y,"stroke-width":i,size:s=l.width,color:v=l.stroke,...r},{slots:k})=>d("svg",{...l,...r,width:s,height:s,stroke:v,"stroke-width":p(h)||p(t)||h===!0||t===!0?Number(y||i||l["stroke-width"])*24/Number(s):y||i||l["stroke-width"],class:m("lucide",r.class,...c?[`lucide-${o(z(c))}-icon`,`lucide-${o(c)}`]:["lucide-icon"]),...!k.default&&!M(r)&&{"aria-hidden":"true"}},[...e.map(n=>d(...n)),...k.default?[k.default()]:[]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const a=(c,e)=>(h,{slots:t,attrs:y})=>d(g,{...y,...h,iconNode:e,name:c},t);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const w=a("activity",[["path",{d:"M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2",key:"169zse"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const V=a("boxes",[["path",{d:"M2.97 12.92A2 2 0 0 0 2 14.63v3.24a2 2 0 0 0 .97 1.71l3 1.8a2 2 0 0 0 2.06 0L12 19v-5.5l-5-3-4.03 2.42Z",key:"lc1i9w"}],["path",{d:"m7 16.5-4.74-2.85",key:"1o9zyk"}],["path",{d:"m7 16.5 5-3",key:"va8pkn"}],["path",{d:"M7 16.5v5.17",key:"jnp8gn"}],["path",{d:"M12 13.5V19l3.97 2.38a2 2 0 0 0 2.06 0l3-1.8a2 2 0 0 0 .97-1.71v-3.24a2 2 0 0 0-.97-1.71L17 10.5l-5 3Z",key:"8zsnat"}],["path",{d:"m17 16.5-5-3",key:"8arw3v"}],["path",{d:"m17 16.5 4.74-2.85",key:"8rfmw"}],["path",{d:"M17 16.5v5.17",key:"k6z78m"}],["path",{d:"M7.97 4.42A2 2 0 0 0 7 6.13v4.37l5 3 5-3V6.13a2 2 0 0 0-.97-1.71l-3-1.8a2 2 0 0 0-2.06 0l-3 1.8Z",key:"1xygjf"}],["path",{d:"M12 8 7.26 5.15",key:"1vbdud"}],["path",{d:"m12 8 4.74-2.85",key:"3rx089"}],["path",{d:"M12 13.5V8",key:"1io7kd"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const f=a("camera",[["path",{d:"M13.997 4a2 2 0 0 1 1.76 1.05l.486.9A2 2 0 0 0 18.003 7H20a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2h1.997a2 2 0 0 0 1.759-1.048l.489-.904A2 2 0 0 1 10.004 4z",key:"18u6gg"}],["circle",{cx:"12",cy:"13",r:"3",key:"1vg3eu"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const C=a("chart-column",[["path",{d:"M3 3v16a2 2 0 0 0 2 2h16",key:"c24i48"}],["path",{d:"M18 17V9",key:"2bz60n"}],["path",{d:"M13 17V5",key:"1frdt8"}],["path",{d:"M8 17v-3",key:"17ska0"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const A=a("check",[["path",{d:"M20 6 9 17l-5-5",key:"1gmf2c"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const L=a("chevron-down",[["path",{d:"m6 9 6 6 6-6",key:"qrunsl"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const j=a("chevron-left",[["path",{d:"m15 18-6-6 6-6",key:"1wnfg3"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const b=a("circle",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const H=a("cloud",[["path",{d:"M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z",key:"p7xjir"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const q=a("copy",[["rect",{width:"14",height:"14",x:"8",y:"8",rx:"2",ry:"2",key:"17jyea"}],["path",{d:"M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2",key:"zix9uf"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Z=a("cpu",[["path",{d:"M12 20v2",key:"1lh1kg"}],["path",{d:"M12 2v2",key:"tus03m"}],["path",{d:"M17 20v2",key:"1rnc9c"}],["path",{d:"M17 2v2",key:"11trls"}],["path",{d:"M2 12h2",key:"1t8f8n"}],["path",{d:"M2 17h2",key:"7oei6x"}],["path",{d:"M2 7h2",key:"asdhe0"}],["path",{d:"M20 12h2",key:"1q8mjw"}],["path",{d:"M20 17h2",key:"1fpfkl"}],["path",{d:"M20 7h2",key:"1o8tra"}],["path",{d:"M7 20v2",key:"4gnj0m"}],["path",{d:"M7 2v2",key:"1i4yhu"}],["rect",{x:"4",y:"4",width:"16",height:"16",rx:"2",key:"1vbyd7"}],["rect",{x:"8",y:"8",width:"8",height:"8",rx:"1",key:"z9xiuo"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const F=a("database",[["ellipse",{cx:"12",cy:"5",rx:"9",ry:"3",key:"msslwz"}],["path",{d:"M3 5V19A9 3 0 0 0 21 19V5",key:"1wlel7"}],["path",{d:"M3 12A9 3 0 0 0 21 12",key:"mv7ke4"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const B=a("external-link",[["path",{d:"M15 3h6v6",key:"1q9fwt"}],["path",{d:"M10 14 21 3",key:"gplh6r"}],["path",{d:"M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",key:"a6xqqp"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const P=a("eye",[["path",{d:"M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0",key:"1nclc0"}],["circle",{cx:"12",cy:"12",r:"3",key:"1v7zrd"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const E=a("film",[["rect",{width:"18",height:"18",x:"3",y:"3",rx:"2",key:"afitv7"}],["path",{d:"M7 3v18",key:"bbkbws"}],["path",{d:"M3 7.5h4",key:"zfgn84"}],["path",{d:"M3 12h18",key:"1i2n21"}],["path",{d:"M3 16.5h4",key:"1230mu"}],["path",{d:"M17 3v18",key:"in4fa5"}],["path",{d:"M17 7.5h4",key:"myr1c1"}],["path",{d:"M17 16.5h4",key:"go4c1d"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const S=a("folder-tree",[["path",{d:"M20 10a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1h-2.5a1 1 0 0 1-.8-.4l-.9-1.2A1 1 0 0 0 15 3h-2a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z",key:"hod4my"}],["path",{d:"M20 21a1 1 0 0 0 1-1v-3a1 1 0 0 0-1-1h-2.9a1 1 0 0 1-.88-.55l-.42-.85a1 1 0 0 0-.92-.6H13a1 1 0 0 0-1 1v5a1 1 0 0 0 1 1Z",key:"w4yl2u"}],["path",{d:"M3 5a2 2 0 0 0 2 2h3",key:"f2jnh7"}],["path",{d:"M3 3v13a2 2 0 0 0 2 2h3",key:"k8epm1"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const D=a("folder",[["path",{d:"M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z",key:"1kt360"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const G=a("gauge",[["path",{d:"m12 14 4-4",key:"9kzdfg"}],["path",{d:"M3.34 19a10 10 0 1 1 17.32 0",key:"19p75a"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const T=a("git-branch",[["path",{d:"M15 6a9 9 0 0 0-9 9V3",key:"1cii5b"}],["circle",{cx:"18",cy:"6",r:"3",key:"1h7g24"}],["circle",{cx:"6",cy:"18",r:"3",key:"fqmcym"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const R=a("globe",[["circle",{cx:"12",cy:"12",r:"10",key:"1mglay"}],["path",{d:"M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20",key:"13o1zl"}],["path",{d:"M2 12h20",key:"9i4pu4"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const $=a("grip-vertical",[["circle",{cx:"9",cy:"12",r:"1",key:"1vctgf"}],["circle",{cx:"9",cy:"5",r:"1",key:"hp0tcf"}],["circle",{cx:"9",cy:"19",r:"1",key:"fkjjf6"}],["circle",{cx:"15",cy:"12",r:"1",key:"1tmaij"}],["circle",{cx:"15",cy:"5",r:"1",key:"19l28e"}],["circle",{cx:"15",cy:"19",r:"1",key:"f4zoj3"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const N=a("hard-drive",[["path",{d:"M10 16h.01",key:"1bzywj"}],["path",{d:"M2.212 11.577a2 2 0 0 0-.212.896V18a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-5.527a2 2 0 0 0-.212-.896L18.55 5.11A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z",key:"18tbho"}],["path",{d:"M21.946 12.013H2.054",key:"zqlbp7"}],["path",{d:"M6 16h.01",key:"1pmjb7"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const O=a("heart-pulse",[["path",{d:"M2 9.5a5.5 5.5 0 0 1 9.591-3.676.56.56 0 0 0 .818 0A5.49 5.49 0 0 1 22 9.5c0 2.29-1.5 4-3 5.5l-5.492 5.313a2 2 0 0 1-3 .019L5 15c-1.5-1.5-3-3.2-3-5.5",key:"mvr1a0"}],["path",{d:"M3.22 13H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27",key:"auskq0"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const I=a("house",[["path",{d:"M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8",key:"5wwlr5"}],["path",{d:"M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",key:"r6nss1"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const U=a("key-round",[["path",{d:"M2.586 17.414A2 2 0 0 0 2 18.828V21a1 1 0 0 0 1 1h3a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h1a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1h.172a2 2 0 0 0 1.414-.586l.814-.814a6.5 6.5 0 1 0-4-4z",key:"1s6t7t"}],["circle",{cx:"16.5",cy:"7.5",r:".5",fill:"currentColor",key:"w0ekpg"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Y=a("layers",[["path",{d:"M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z",key:"zw3jo"}],["path",{d:"M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12",key:"1wduqc"}],["path",{d:"M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17",key:"kqbvx6"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const J=a("layout-dashboard",[["rect",{width:"7",height:"9",x:"3",y:"3",rx:"1",key:"10lvy0"}],["rect",{width:"7",height:"5",x:"14",y:"3",rx:"1",key:"16une8"}],["rect",{width:"7",height:"9",x:"14",y:"12",rx:"1",key:"1hutg5"}],["rect",{width:"7",height:"5",x:"3",y:"16",rx:"1",key:"ldoo1y"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const Q=a("link-2",[["path",{d:"M9 17H7A5 5 0 0 1 7 7h2",key:"8i5ue5"}],["path",{d:"M15 7h2a5 5 0 1 1 0 10h-2",key:"1b9ql8"}],["line",{x1:"8",x2:"16",y1:"12",y2:"12",key:"1jonct"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const _=a("lock",[["rect",{width:"18",height:"11",x:"3",y:"11",rx:"2",ry:"2",key:"1w4ew1"}],["path",{d:"M7 11V7a5 5 0 0 1 10 0v4",key:"fwvmzm"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const K=a("map-pin",[["path",{d:"M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0",key:"1r0f0z"}],["circle",{cx:"12",cy:"10",r:"3",key:"ilqhr7"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const W=a("monitor-smartphone",[["path",{d:"M18 8V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h8",key:"10dyio"}],["path",{d:"M10 19v-3.96 3.15",key:"1irgej"}],["path",{d:"M7 19h5",key:"qswx4l"}],["rect",{width:"6",height:"10",x:"16",y:"12",rx:"2",key:"1egngj"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const X=a("monitor",[["rect",{width:"20",height:"14",x:"2",y:"3",rx:"2",key:"48i651"}],["line",{x1:"8",x2:"16",y1:"21",y2:"21",key:"1svkeh"}],["line",{x1:"12",x2:"12",y1:"17",y2:"21",key:"vw1qmm"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const a0=a("music",[["path",{d:"M9 18V5l12-2v13",key:"1jmyc2"}],["circle",{cx:"6",cy:"18",r:"3",key:"fqmcym"}],["circle",{cx:"18",cy:"16",r:"3",key:"1hluhg"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const c0=a("network",[["rect",{x:"16",y:"16",width:"6",height:"6",rx:"1",key:"4q2zg0"}],["rect",{x:"2",y:"16",width:"6",height:"6",rx:"1",key:"8cvhb9"}],["rect",{x:"9",y:"2",width:"6",height:"6",rx:"1",key:"1egb70"}],["path",{d:"M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3",key:"1jsf9p"}],["path",{d:"M12 12V8",key:"2874zd"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const e0=a("package",[["path",{d:"M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z",key:"1a0edw"}],["path",{d:"M12 22V12",key:"d0xqtd"}],["polyline",{points:"3.29 7 12 12 20.71 7",key:"ousv84"}],["path",{d:"m7.5 4.27 9 5.15",key:"1c824w"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const t0=a("pencil",[["path",{d:"M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z",key:"1a8usu"}],["path",{d:"m15 5 4 4",key:"1mk7zo"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const h0=a("plus",[["path",{d:"M5 12h14",key:"1ays0h"}],["path",{d:"M12 5v14",key:"s699le"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const l0=a("radar",[["path",{d:"M19.07 4.93A10 10 0 0 0 6.99 3.34",key:"z3du51"}],["path",{d:"M4 6h.01",key:"oypzma"}],["path",{d:"M2.29 9.62A10 10 0 1 0 21.31 8.35",key:"qzzz0"}],["path",{d:"M16.24 7.76A6 6 0 1 0 8.23 16.67",key:"1yjesh"}],["path",{d:"M12 18h.01",key:"mhygvu"}],["path",{d:"M17.99 11.66A6 6 0 0 1 15.77 16.67",key:"1u2y91"}],["circle",{cx:"12",cy:"12",r:"2",key:"1c9p78"}],["path",{d:"m13.41 10.59 5.66-5.66",key:"mhq4k0"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const y0=a("refresh-cw",[["path",{d:"M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8",key:"v9h5vc"}],["path",{d:"M21 3v5h-5",key:"1q7to0"}],["path",{d:"M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16",key:"3uifl3"}],["path",{d:"M8 16H3v5",key:"1cv678"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const s0=a("route",[["circle",{cx:"6",cy:"19",r:"3",key:"1kj8tv"}],["path",{d:"M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15",key:"1d8sl"}],["circle",{cx:"18",cy:"5",r:"3",key:"gq8acd"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const r0=a("search",[["path",{d:"m21 21-4.34-4.34",key:"14j7rj"}],["circle",{cx:"11",cy:"11",r:"8",key:"4ej97u"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const k0=a("server",[["rect",{width:"20",height:"8",x:"2",y:"2",rx:"2",ry:"2",key:"ngkwjq"}],["rect",{width:"20",height:"8",x:"2",y:"14",rx:"2",ry:"2",key:"iecqi9"}],["line",{x1:"6",x2:"6.01",y1:"6",y2:"6",key:"16zg32"}],["line",{x1:"6",x2:"6.01",y1:"18",y2:"18",key:"nzw8ys"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const d0=a("settings",[["path",{d:"M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915",key:"1i5ecw"}],["circle",{cx:"12",cy:"12",r:"3",key:"1v7zrd"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const i0=a("shield",[["path",{d:"M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z",key:"oel41y"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const p0=a("sliders-horizontal",[["path",{d:"M10 5H3",key:"1qgfaw"}],["path",{d:"M12 19H3",key:"yhmn1j"}],["path",{d:"M14 3v4",key:"1sua03"}],["path",{d:"M16 17v4",key:"1q0r14"}],["path",{d:"M21 12h-9",key:"1o4lsq"}],["path",{d:"M21 19h-5",key:"1rlt1p"}],["path",{d:"M21 5h-7",key:"1oszz2"}],["path",{d:"M8 10v4",key:"tgpxqk"}],["path",{d:"M8 12H3",key:"a7s4jb"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const o0=a("sparkles",[["path",{d:"M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z",key:"1s2grr"}],["path",{d:"M20 2v4",key:"1rf3ol"}],["path",{d:"M22 4h-4",key:"gwowj6"}],["circle",{cx:"4",cy:"20",r:"2",key:"6kqj1y"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const v0=a("terminal",[["path",{d:"M12 19h8",key:"baeox8"}],["path",{d:"m4 17 6-6-6-6",key:"1yngyt"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const n0=a("trash-2",[["path",{d:"M10 11v6",key:"nco0om"}],["path",{d:"M14 11v6",key:"outv1u"}],["path",{d:"M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6",key:"miytrc"}],["path",{d:"M3 6h18",key:"d0wm0j"}],["path",{d:"M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2",key:"e791ji"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const M0=a("triangle-alert",[["path",{d:"m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3",key:"wmoenq"}],["path",{d:"M12 9v4",key:"juzpu7"}],["path",{d:"M12 17h.01",key:"p32p05"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const m0=a("tv",[["path",{d:"m17 2-5 5-5-5",key:"16satq"}],["rect",{width:"20",height:"15",x:"2",y:"7",rx:"2",key:"1e6viu"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const x0=a("wifi",[["path",{d:"M12 20h.01",key:"zekei9"}],["path",{d:"M2 8.82a15 15 0 0 1 20 0",key:"dnpr2z"}],["path",{d:"M5 12.859a10 10 0 0 1 14 0",key:"1x1e6c"}],["path",{d:"M8.5 16.429a5 5 0 0 1 7 0",key:"1bycff"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const z0=a("workflow",[["rect",{width:"8",height:"8",x:"3",y:"3",rx:"2",key:"by2w9f"}],["path",{d:"M7 11v4a2 2 0 0 0 2 2h4",key:"xkn7yn"}],["rect",{width:"8",height:"8",x:"13",y:"13",rx:"2",key:"1cgmvn"}]]);/**
 * @license lucide-vue-next v0.575.0 - ISC
 *
 * This source code is licensed under the ISC license.
 * See the LICENSE file in the root directory of this source tree.
 */const g0=a("wrench",[["path",{d:"M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.106-3.105c.32-.322.863-.22.983.218a6 6 0 0 1-8.259 7.057l-7.91 7.91a1 1 0 0 1-2.999-3l7.91-7.91a6 6 0 0 1 7.057-8.259c.438.12.54.662.219.984z",key:"1ngwbx"}]]),u0={path:"M12 0C8.249 0 3.725.861 0 2.755 0 6.845-.051 17.037 12 24 24.051 17.037 24 6.845 24 2.755 20.275.861 15.751 0 12 0zm-.106 15.429L6.857 9.612c.331-.239 1.75-1.143 2.794.042l2.187 2.588c.009-.001 5.801-5.948 5.815-5.938.246-.22.694-.503 1.204-.101l-6.963 9.226z",hex:"68BC71"},w0={path:"M12 0C5.383 0 0 5.382 0 12s5.383 12 12 12 12-5.383 12-12S18.617 0 12 0zm0 1.799A10.19 10.19 0 0 1 22.207 12 10.19 10.19 0 0 1 12 22.201 10.186 10.186 0 0 1 1.799 12 10.186 10.186 0 0 1 12 1.799zm4.016 5.285c-.49-.018-1.232.368-1.899 1.031l-1.44 1.43-4.31-1.447-.842.867 3.252 2.47-.728.723a4.747 4.747 0 0 0-.639.787L7.451 12.8l-.476.484 1.947 1.444 1.424 1.943.48-.48-.144-1.98c.246-.16.497-.361.74-.603l.765-.76 2.495 3.274.869-.84-1.455-4.332 1.394-1.385c.89-.885 1.298-1.92.918-2.322a.547.547 0 0 0-.392-.158z",hex:"0066CC"},V0={path:"M13.983 11.078h2.119a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.119a.185.185 0 00-.185.185v1.888c0 .102.083.185.185.185m-2.954-5.43h2.118a.186.186 0 00.186-.186V3.574a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m0 2.716h2.118a.187.187 0 00.186-.186V6.29a.186.186 0 00-.186-.185h-2.118a.185.185 0 00-.185.185v1.887c0 .102.082.185.185.186m-2.93 0h2.12a.186.186 0 00.184-.186V6.29a.185.185 0 00-.185-.185H8.1a.185.185 0 00-.185.185v1.887c0 .102.083.185.185.186m-2.964 0h2.119a.186.186 0 00.185-.186V6.29a.185.185 0 00-.185-.185H5.136a.186.186 0 00-.186.185v1.887c0 .102.084.185.186.186m5.893 2.715h2.118a.186.186 0 00.186-.185V9.006a.186.186 0 00-.186-.186h-2.118a.185.185 0 00-.185.185v1.888c0 .102.082.185.185.185m-2.93 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.083.185.185.185m-2.964 0h2.119a.185.185 0 00.185-.185V9.006a.185.185 0 00-.184-.186h-2.12a.186.186 0 00-.186.186v1.887c0 .102.084.185.186.185m-2.92 0h2.12a.185.185 0 00.184-.185V9.006a.185.185 0 00-.184-.186h-2.12a.185.185 0 00-.184.185v1.888c0 .102.082.185.185.185M23.763 9.89c-.065-.051-.672-.51-1.954-.51-.338.001-.676.03-1.01.087-.248-1.7-1.653-2.53-1.716-2.566l-.344-.199-.226.327c-.284.438-.49.922-.612 1.43-.23.97-.09 1.882.403 2.661-.595.332-1.55.413-1.744.42H.751a.751.751 0 00-.75.748 11.376 11.376 0 00.692 4.062c.545 1.428 1.355 2.48 2.41 3.124 1.18.723 3.1 1.137 5.275 1.137.983.003 1.963-.086 2.93-.266a12.248 12.248 0 003.823-1.389c.98-.567 1.86-1.288 2.61-2.136 1.252-1.418 1.998-2.997 2.553-4.4h.221c1.372 0 2.215-.549 2.68-1.009.309-.293.55-.65.707-1.046l.098-.288Z",hex:"2496ED"},f0={path:"M4.209 4.603c-.247 0-.525.02-.84.088-.333.07-1.28.283-2.054 1.027C-.403 7.25.035 9.685.089 10.052c.065.446.263 1.687 1.21 2.768 1.749 2.141 5.513 2.092 5.513 2.092s.462 1.103 1.168 2.119c.955 1.263 1.936 2.248 2.89 2.367 2.406 0 7.212-.004 7.212-.004s.458.004 1.08-.394c.535-.324 1.013-.893 1.013-.893s.492-.527 1.18-1.73c.21-.37.385-.729.538-1.068 0 0 2.107-4.471 2.107-8.823-.042-1.318-.367-1.55-.443-1.627-.156-.156-.366-.153-.366-.153s-4.475.252-6.792.306c-.508.011-1.012.023-1.512.027v4.474l-.634-.301c0-1.39-.004-4.17-.004-4.17-1.107.016-3.405-.084-3.405-.084s-5.399-.27-5.987-.324c-.187-.011-.401-.032-.648-.032zm.354 1.832h.111s.271 2.269.6 3.597C5.549 11.147 6.22 13 6.22 13s-.996-.119-1.641-.348c-.99-.324-1.409-.714-1.409-.714s-.73-.511-1.096-1.52C1.444 8.73 2.021 7.7 2.021 7.7s.32-.859 1.47-1.145c.395-.106.863-.12 1.072-.12zm8.33 2.554c.26.003.509.127.509.127l.868.422-.529 1.075a.686.686 0 0 0-.614.359.685.685 0 0 0 .072.756l-.939 1.924a.69.69 0 0 0-.66.527.687.687 0 0 0 .347.763.686.686 0 0 0 .867-.206.688.688 0 0 0-.069-.882l.916-1.874a.667.667 0 0 0 .237-.02.657.657 0 0 0 .271-.137 8.826 8.826 0 0 1 1.016.512.761.761 0 0 1 .286.282c.073.21-.073.569-.073.569-.087.29-.702 1.55-.702 1.55a.692.692 0 0 0-.676.477.681.681 0 1 0 1.157-.252c.073-.141.141-.282.214-.431.19-.397.515-1.16.515-1.16.035-.066.218-.394.103-.814-.095-.435-.48-.638-.48-.638-.467-.301-1.116-.58-1.116-.58s0-.156-.042-.27a.688.688 0 0 0-.148-.241l.516-1.062 2.89 1.401s.48.218.583.619c.073.282-.019.534-.069.657-.24.587-2.1 4.317-2.1 4.317s-.232.554-.748.588a1.065 1.065 0 0 1-.393-.045l-.202-.08-4.31-2.1s-.417-.218-.49-.596c-.083-.31.104-.691.104-.691l2.073-4.272s.183-.37.466-.497a.855.855 0 0 1 .35-.077z",hex:"609926"},C0={path:"M23.02 10.59a8.578 8.578 0 0 0-.862-3.034 8.911 8.911 0 0 0-1.789-2.445c.337-1.342-.413-2.505-.413-2.505-1.292-.08-2.113.4-2.416.62-.052-.02-.102-.044-.154-.064-.22-.089-.446-.172-.677-.247-.231-.073-.47-.14-.711-.197a9.867 9.867 0 0 0-.875-.161C14.557.753 12.94 0 12.94 0c-1.804 1.145-2.147 2.744-2.147 2.744l-.018.093c-.098.029-.2.057-.298.088-.138.042-.275.094-.413.143-.138.055-.275.107-.41.166a8.869 8.869 0 0 0-1.557.87l-.063-.029c-2.497-.955-4.716.195-4.716.195-.203 2.658.996 4.33 1.235 4.636a11.608 11.608 0 0 0-.607 2.635C1.636 12.677.953 15.014.953 15.014c1.926 2.214 4.171 2.351 4.171 2.351.003-.002.006-.002.006-.005.285.509.615.994.986 1.446.156.19.32.371.488.548-.704 2.009.099 3.68.099 3.68 2.144.08 3.553-.937 3.849-1.173a9.784 9.784 0 0 0 3.164.501h.08l.055-.003.107-.002.103-.005.003.002c1.01 1.44 2.788 1.646 2.788 1.646 1.264-1.332 1.337-2.653 1.337-2.94v-.058c0-.02-.003-.039-.003-.06.265-.187.52-.387.758-.6a7.875 7.875 0 0 0 1.415-1.7c1.43.083 2.437-.885 2.437-.885-.236-1.49-1.085-2.216-1.264-2.354l-.018-.013-.016-.013a.217.217 0 0 1-.031-.02c.008-.092.016-.18.02-.27.011-.162.016-.323.016-.48v-.253l-.005-.098-.008-.135a1.891 1.891 0 0 0-.01-.13c-.003-.042-.008-.083-.013-.125l-.016-.124-.018-.122a6.215 6.215 0 0 0-2.032-3.73 6.015 6.015 0 0 0-3.222-1.46 6.292 6.292 0 0 0-.85-.048l-.107.002h-.063l-.044.003-.104.008a4.777 4.777 0 0 0-3.335 1.695c-.332.4-.592.84-.768 1.297a4.594 4.594 0 0 0-.312 1.817l.003.091c.005.055.007.11.013.164a3.615 3.615 0 0 0 .698 1.82 3.53 3.53 0 0 0 1.827 1.282c.33.098.66.14.971.137.039 0 .078 0 .114-.002l.063-.003c.02 0 .041-.003.062-.003.034-.002.065-.007.099-.01.007 0 .018-.003.028-.003l.031-.005.06-.008a1.18 1.18 0 0 0 .112-.02c.036-.008.072-.013.109-.024a2.634 2.634 0 0 0 .914-.415c.028-.02.056-.041.085-.065a.248.248 0 0 0 .039-.35.244.244 0 0 0-.309-.06l-.078.042c-.09.044-.184.083-.283.116a2.476 2.476 0 0 1-.475.096c-.028.003-.054.006-.083.006l-.083.002c-.026 0-.054 0-.08-.002l-.102-.006h-.012l-.024.006c-.016-.003-.031-.003-.044-.006-.031-.002-.06-.007-.091-.01a2.59 2.59 0 0 1-.724-.213 2.557 2.557 0 0 1-.667-.438 2.52 2.52 0 0 1-.805-1.475 2.306 2.306 0 0 1-.029-.444l.006-.122v-.023l.002-.031c.003-.021.003-.04.005-.06a3.163 3.163 0 0 1 1.352-2.29 3.12 3.12 0 0 1 .937-.43 2.946 2.946 0 0 1 .776-.101h.06l.07.002.045.003h.026l.07.005a4.041 4.041 0 0 1 1.635.49 3.94 3.94 0 0 1 1.602 1.662 3.77 3.77 0 0 1 .397 1.414l.005.076.003.075c.002.026.002.05.002.075 0 .024.003.052 0 .07v.065l-.002.073-.008.174a6.195 6.195 0 0 1-.08.639 5.1 5.1 0 0 1-.267.927 5.31 5.31 0 0 1-.624 1.13 5.052 5.052 0 0 1-3.237 2.014 4.82 4.82 0 0 1-.649.066l-.039.003h-.287a6.607 6.607 0 0 1-1.716-.265 6.776 6.776 0 0 1-3.4-2.274 6.75 6.75 0 0 1-.746-1.15 6.616 6.616 0 0 1-.714-2.596l-.005-.083-.002-.02v-.056l-.003-.073v-.096l-.003-.104v-.07l.003-.163c.008-.22.026-.45.054-.678a8.707 8.707 0 0 1 .28-1.355c.128-.444.286-.872.473-1.277a7.04 7.04 0 0 1 1.456-2.1 5.925 5.925 0 0 1 .953-.763c.169-.111.343-.213.524-.306.089-.05.182-.091.273-.135.047-.02.093-.042.138-.062a7.177 7.177 0 0 1 .714-.267l.145-.045c.049-.015.098-.026.148-.041.098-.029.197-.052.296-.076.049-.013.1-.02.15-.033l.15-.032.151-.028.076-.013.075-.01.153-.024c.057-.01.114-.013.171-.023l.169-.021c.036-.003.073-.008.106-.01l.073-.008.036-.003.042-.002c.057-.003.114-.008.171-.01l.086-.006h.023l.037-.003.145-.007a7.999 7.999 0 0 1 1.708.125 7.917 7.917 0 0 1 2.048.68 8.253 8.253 0 0 1 1.672 1.09l.09.077.089.078c.06.052.114.107.171.159.057.052.112.106.166.16.052.055.107.107.159.164a8.671 8.671 0 0 1 1.41 1.978c.012.026.028.052.04.078l.04.078.075.156c.023.051.05.1.07.153l.065.15a8.848 8.848 0 0 1 .45 1.34.19.19 0 0 0 .201.142.186.186 0 0 0 .172-.184c.01-.246.002-.532-.024-.856z",hex:"F46800"},A0={path:"M22.939 10.627 13.061.749a1.505 1.505 0 0 0-2.121 0l-9.879 9.878C.478 11.21 0 12.363 0 13.187v9c0 .826.675 1.5 1.5 1.5h9.227l-4.063-4.062a2.034 2.034 0 0 1-.664.113c-1.13 0-2.05-.92-2.05-2.05s.92-2.05 2.05-2.05 2.05.92 2.05 2.05c0 .233-.041.456-.113.665l3.163 3.163V9.928a2.05 2.05 0 0 1-1.15-1.84c0-1.13.92-2.05 2.05-2.05s2.05.92 2.05 2.05a2.05 2.05 0 0 1-1.15 1.84v8.127l3.146-3.146A2.051 2.051 0 0 1 18 12.239c1.13 0 2.05.92 2.05 2.05s-.92 2.05-2.05 2.05c-.25 0-.488-.047-.709-.13L12.9 20.602v3.088h9.6c.825 0 1.5-.675 1.5-1.5v-9c0-.825-.477-1.977-1.061-2.561z",hex:"18BCF2"},L0={path:"M12 .002C8.826.002-1.398 18.537.16 21.666c1.56 3.129 22.14 3.094 23.682 0C25.384 18.573 15.177 0 12 0zm7.76 18.949c-1.008 2.028-14.493 2.05-15.514 0C3.224 16.9 9.92 4.755 12.003 4.755c2.081 0 8.77 12.166 7.759 14.196zM12 9.198c-1.054 0-4.446 6.15-3.93 7.189.518 1.04 7.348 1.027 7.86 0 .511-1.027-2.874-7.19-3.93-7.19z",hex:"00A4DC"},j0={path:"M12 0L1.605 6v12L12 24l10.395-6V6L12 0zm6 16.59c0 .705-.646 1.29-1.529 1.29-.631 0-1.351-.255-1.801-.81l-6-7.141v6.66c0 .721-.57 1.29-1.274 1.29H7.32c-.721 0-1.29-.6-1.29-1.29V7.41c0-.705.63-1.29 1.5-1.29.646 0 1.38.255 1.83.81l5.97 7.141V7.41c0-.721.6-1.29 1.29-1.29h.075c.72 0 1.29.6 1.29 1.29v9.18H18z",hex:"009639"},b0={path:"M12.008 0A822.933 822.933 0 0 0 1.59 6.043V18c3.578 2.087 7.238 4.274 10.418 6 3.928-2.267 6.71-3.868 10.402-6v-3.043l-1.045.6v1.8l-1.545.9-1.56-.9v-1.8l1.56-.885v-.002l.268.156a8.15 8.15 0 0 0 .404-1.754v-.002a8.72 8.72 0 0 0 .072-1.072 9.885 9.885 0 0 0-.072-1.127 8.873 8.873 0 0 0-.515-1.97v-.003a8.137 8.137 0 0 0-1.301-2.242 7.113 7.113 0 0 0-.615-.699 10.271 10.271 0 0 0-.846-.728 7.91 7.91 0 0 0-1.902-1.116 4.776 4.776 0 0 0-.586-.213v-.957c.41.118.812.265 1.2.442a9.2 9.2 0 0 1 1.618.943 9.4 9.4 0 0 1 1.158.986c.273.277.53.568.774.872.532.686.97 1.44 1.302 2.244h-.002a9.45 9.45 0 0 1 .645 2.613c.04.317.06.637.056.957 0 .314-.014.614-.043.914-.082.838-.37 1.786-.542 2.373l.472.27 1.045-.602V8.986l-1.303-.742v-.002l1.303.744V6c-3.56-2.057-7.212-4.154-10.402-6Zm8.08 14.826c-.02.052.003.002.004.002zM12.035 1.213l1.56.9v1.801l-1.56.885-1.545-.885h-.002v-.328a8.458 8.458 0 0 0-1.744.516 8.178 8.178 0 0 0-1.889 1.07l-.001.002a6.77 6.77 0 0 0-.9.783 9.171 9.171 0 0 0-.616.672 8.84 8.84 0 0 0-1.3 2.228l.228.127 1.287-.742 1.203.686c1.929-1.112 3.397-1.961 5.252-3.014l.027.014c1.926 1.114 3.398 1.955 5.238 3.029.028 1.997.014 4.064.014 6.086-1.874 1.084-3.753 2.16-5.28 3.043a859.719 859.719 0 0 1-5.294-3.043V8.957l.043-.027-1.203-.688-1.287.744-.229-.129h-.002a8.376 8.376 0 0 0-.53 2.057c-.044.36-.068.723-.07 1.086.002.344.026.687.07 1.027v.002c.015.215.06.429.102.643l-.83.484a7.017 7.017 0 0 1-.2-1.199A7.065 7.065 0 0 1 2.52 12c0-.329.028-.672.056-1a9.77 9.77 0 0 1 .658-2.6 9.438 9.438 0 0 1 1.303-2.244c.243-.3.5-.57.758-.842.37-.372.773-.71 1.203-1.013-1.215-.084-1.215-.084 0-.002a9.394 9.394 0 0 1 1.645-.942 9.866 9.866 0 0 1 2.347-.7l-.002-.542-1.043-.601 1.045.6zm0 .773-.887.514v1.027l.887.516.887-.516V2.5Zm-.03 6.928c-.935.532-1.888 1.084-2.689 1.543v3.086c.933.535 1.892 1.095 2.692 1.557.926-.565 1.865-1.093 2.676-1.557v-3.086c-.945-.542-1.857-1.074-2.678-1.543Zm-7.74 5.758 1.546.885v1.8l-.329.186c.146.177.303.344.471.5.277.288.58.55.902.785a8.07 8.07 0 0 0 1.83 1.059h.002a8.14 8.14 0 0 0 2.061.57c.417.058.837.087 1.258.086a8.37 8.37 0 0 0 1.332-.1 8.64 8.64 0 0 0 2.017-.572 8.076 8.076 0 0 0 1.86-1.1c.172-.114.315-.242.472-.37l.83.47a9.79 9.79 0 0 1-.945.787l.946.541 1.302-.756-1.302.758-.946-.543c-.516.37-1.067.69-1.644.955l-.002.002a9.502 9.502 0 0 1-2.588.756c-.441.057-.885.086-1.33.086a12.048 12.048 0 0 1-1.26-.072v.002a9.38 9.38 0 0 1-2.605-.744 9.044 9.044 0 0 1-1.688-.971 9.625 9.625 0 0 1-1.775-1.658h-.002l-.412.244-1.56-.9v-1.801zm0 .756-.886.515v1.028l.887.515.886-.515v-1.028zm15.555 0-.902.515v1.028l.902.515.887-.515v-1.028z",hex:"F15833"},H0={path:"M24 9.736V9.72c0-.018-.009-.035-.009-.053-.008-.017-.008-.034-.017-.052 0-.009-.009-.009-.009-.017a.19.19 0 0 0-.026-.044v-.009c-.009-.017-.026-.026-.044-.043l-.008-.009c-.018-.009-.035-.026-.053-.035l-3.72-2.143V3.02c0-.018 0-.044-.008-.061V2.94a.124.124 0 0 0-.017-.052V2.88c-.01-.017-.018-.035-.027-.043 0-.01-.008-.01-.008-.01a.19.19 0 0 0-.035-.043c-.018-.008-.026-.026-.044-.034-.008 0-.008-.01-.017-.01l-.009-.008L16.055.476a.338.338 0 0 0-.34 0l-3.72 2.143L8.286.476a.338.338 0 0 0-.34 0L4.06 2.723c-.01 0-.01.01-.01.01-.008 0-.008.008-.017.008-.017.009-.026.026-.043.035a.153.153 0 0 0-.035.043l-.009.009c-.008.017-.017.026-.026.044v.008c-.009.018-.009.035-.017.052v.018c0 .017-.009.043-.009.06v4.296L.166 9.457c-.018.01-.035.026-.053.035l-.008.009-.044.043v.01c-.009.017-.017.025-.026.043 0 .008-.009.008-.009.017a.124.124 0 0 0-.017.052C0 9.684 0 9.701 0 9.72v4.521a.34.34 0 0 0 .166.296l3.72 2.143v4.295a.34.34 0 0 0 .165.296l3.885 2.248c.009.008.018.008.026.017 0 0 .009 0 .009.009.009 0 .017.008.026.008.009 0 .009 0 .018.01.008 0 .017 0 .026.008h.061a.35.35 0 0 0 .13-.026c.018-.009.026-.009.044-.018l3.72-2.143 3.72 2.143c.017.009.026.018.043.018a.35.35 0 0 0 .13.026h.062c.008 0 .017 0 .026-.009.008 0 .008 0 .017-.009.009 0 .018-.008.026-.008.009 0 .009 0 .009-.009.009 0 .017-.009.026-.017l3.885-2.248a.34.34 0 0 0 .166-.296V16.68l3.72-2.143a.34.34 0 0 0 .165-.296V9.754c.009-.01.009-.018.009-.018zM12.17 20.67s-.009 0-.009-.009c-.009-.008-.017-.008-.035-.017-.008 0-.017-.009-.026-.009-.009 0-.017-.009-.035-.009-.008 0-.026-.008-.035-.008h-.069c-.009 0-.026 0-.035.008-.009 0-.017 0-.035.01-.009 0-.017.008-.026.008-.009.009-.017.009-.035.017 0 0-.009 0-.009.009l-3.37 1.951v-3.702l3.545-2.047 3.545 2.047v3.702zM4.4 7.793c.017-.017.025-.026.034-.026.009-.008.018-.008.026-.017l.026-.026c.01-.009.018-.018.018-.026.009-.01.009-.018.017-.026.009-.01.009-.018.018-.027.008-.008.008-.017.008-.034 0-.01.01-.018.01-.035 0-.009 0-.018.008-.035V3.603L7.77 5.46v4.094L4.225 11.6 1.02 9.745zm7.596-4.381l3.545 2.047V9.16l-3.38-1.951s-.009 0-.009-.009c-.008-.009-.017-.009-.034-.017-.01 0-.018-.009-.027-.009-.008 0-.017-.009-.034-.009-.01 0-.018-.008-.035-.008h-.07c-.009 0-.026 0-.035.008-.008 0-.017 0-.035.009-.008 0-.017.009-.026.009-.008.008-.026.008-.035.017 0 0-.008 0-.008.009L8.45 9.16v-3.7zm0 12.675L8.45 14.04V9.945l3.546-2.047 3.545 2.047v4.095zm-7.431-3.903l3.206-1.856v3.947c0 .008 0 .017.008.035 0 .008.009.017.009.034 0 .01.009.018.009.035.008.009.008.018.017.026.009.01.009.018.018.027.008.008.017.017.017.026l.026.026c.009.009.018.017.026.017.009.009.018.018.026.018l.01.008 3.38 1.952-3.207 1.855-3.545-2.047zm11.325 6.15l-3.206-1.855 3.38-1.952.009-.008c.008-.009.017-.018.026-.018.008-.008.017-.008.026-.017l.026-.026c.009-.009.017-.018.017-.026.01-.01.01-.018.018-.027.009-.008.009-.017.017-.026.009-.008.009-.017.009-.035 0-.008.009-.017.009-.034 0-.01 0-.018.008-.035v-3.947l3.206 1.856v4.094zm3.885-6.734l-3.546-2.047V5.46l3.206-1.856V7.55c0 .008 0 .017.009.034 0 .01.009.018.009.035 0 .009.008.018.008.035.01.009.01.018.018.026.008.009.008.018.017.026.009.01.018.018.018.026.008.01.017.018.026.027.008.008.017.017.026.017.009.009.017.017.026.017l.009.01 3.38 1.95zM15.89 1.164l3.205 1.856-3.205 1.855-3.206-1.855zm-7.78 0l3.206 1.856L8.11 4.866 4.905 3.02zM.68 10.337l3.205 1.856v3.702L.68 14.04zM7.77 22.62l-3.205-1.855v-3.703l3.206 1.856zm11.665-1.846l-3.206 1.855v-3.702l3.206-1.856zm3.886-6.734l-3.206 1.855v-3.702l3.206-1.856Z",hex:"0081A5"},q0={path:"m12 0c-3.906 0-7.4465 1.5949-10.006 4.1543l1.6953 1.6953c2.1278-2.1278 5.069-3.4395 8.3105-3.4395 3.2416 0 6.1833 1.3122 8.3105 3.4395l1.6953-1.6953c-2.56-2.5594-6.0999-4.1543-10.006-4.1543zm0 4.3203c-2.7091 0-5.1685 1.1138-6.9473 2.8926l1.6953 1.6953c1.346-1.346 3.2079-2.1777 5.252-2.1777 2.0435 0 3.9053 0.83172 5.252 2.1777l1.6953-1.6953c-1.7782-1.7782-4.2381-2.8926-6.9473-2.8926zm-7.7285 3.7559c-1.3295 1.6792-2.1113 3.7906-2.1113 6.084 0 5.4189 4.4216 9.8398 9.8398 9.8398 5.4183 0 9.8398-4.4209 9.8398-9.8398 0-2.2934-0.79833-4.4048-2.1113-6.084l-1.7129 1.7129c0.8974 1.2298 1.4297 2.7427 1.4297 4.3711 0 4.1053-3.34 7.4473-7.4453 7.4473-4.1052 0-7.4473-3.342-7.4473-7.4473 0-1.6284 0.53174-3.1413 1.4297-4.3711l-1.7109-1.7129zm7.7285 0.56641c-1.5128 0-2.8928 0.61633-3.9062 1.6133l1.6953 1.6953c1.2219-1.2195 3.2006-1.2195 4.4219 0l1.6953-1.6953c-1.0354-1.0361-2.4416-1.6176-3.9062-1.6133zm0 3.8887c-0.8997 0-1.6289 0.72911-1.6289 1.6289 0 0.8992 0.72921 1.6289 1.6289 1.6289 0.8998 0 1.6289-0.72971 1.6289-1.6289-0.0019-0.8992-0.72971-1.6277-1.6289-1.6289z",hex:"00B5E2"},Z0={path:"M12.504 0v1.023l-.01-.015-6.106 3.526H3.417v.751h5.359v3.638h1.942V5.284h1.786v10.416c.027 0 .54-.01.751.091V5.285h.531v10.608c.293.147.55.312.751.54V5.286h6.046v-.75h-1.267l-6.061-3.5V0zm0 1.87v2.664H7.889zm.751.031l4.56 2.633h-4.56zM9.142 5.285h1.21v1.686h-1.21zm-4.736 2.73v1.951h1.942v-1.95zm2.19 0v1.951h1.941v-1.95zm-2.19 2.171v1.951h1.942v-1.95zm2.19 0v1.951h1.941v-1.95zm2.18 0v1.951h1.942v-1.95zM4.36 12.43a3.73 3.73 0 00-.494 1.851c0 1.227.604 2.308 1.52 2.986.239-.064.477-.1.724-.11.1 0 .165.01.266.019.284-1.191 1.383-1.988 2.665-1.988.724 0 1.438.201 1.924.668.229-.476.302-1.007.302-1.575 0-.65-.165-1.292-.494-1.85zm4.828 3.16c-1.21 0-2.226.844-2.492 1.97a.922.922 0 00-.275-.009 2.559 2.559 0 00-2.564 2.556 2.565 2.565 0 003.096 2.5A2.579 2.579 0 009.233 24c.862 0 1.622-.43 2.09-1.081a2.557 2.557 0 004.186-1.97c0-.567-.193-1.099-.504-1.52a2.557 2.557 0 00-3.866-2.94 2.574 2.574 0 00-1.951-.898z",hex:"13BEF9"},F0={path:"M23.5594 14.7228a.5269.5269 0 0 0-.0563-.1191c-.139-.2632-.4768-.3418-1.0074-.2321-1.6533.3411-2.2935.1312-2.5256-.0191 1.342-2.0482 2.445-4.522 3.0411-6.8297.2714-1.0507.7982-3.5237.1222-4.7316a1.5641 1.5641 0 0 0-.1509-.235C21.6931.9086 19.8007.0248 17.5099.0005c-1.4947-.0158-2.7705.3461-3.1161.4794a9.449 9.449 0 0 0-.5159-.0816 8.044 8.044 0 0 0-1.3114-.1278c-1.1822-.0184-2.2038.2642-3.0498.8406-.8573-.3211-4.7888-1.645-7.2219.0788C.9359 2.1526.3086 3.8733.4302 6.3043c.0409.818.5069 3.334 1.2423 5.7436.4598 1.5065.9387 2.7019 1.4334 3.582.553.9942 1.1259 1.5933 1.7143 1.7895.4474.1491 1.1327.1441 1.8581-.7279.8012-.9635 1.5903-1.8258 1.9446-2.2069.4351.2355.9064.3625 1.39.3772a.0569.0569 0 0 0 .0004.0041 11.0312 11.0312 0 0 0-.2472.3054c-.3389.4302-.4094.5197-1.5002.7443-.3102.064-1.1344.2339-1.1464.8115-.0025.1224.0329.2309.0919.3268.2269.4231.9216.6097 1.015.6331 1.3345.3335 2.5044.092 3.3714-.6787-.017 2.231.0775 4.4174.3454 5.0874.2212.5529.7618 1.9045 2.4692 1.9043.2505 0 .5263-.0291.8296-.0941 1.7819-.3821 2.5557-1.1696 2.855-2.9059.1503-.8707.4016-2.8753.5388-4.1012.0169-.0703.0357-.1207.057-.1362.0007-.0005.0697-.0471.4272.0307a.3673.3673 0 0 0 .0443.0068l.2539.0223.0149.001c.8468.0384 1.9114-.1426 2.5312-.4308.6438-.2988 1.8057-1.0323 1.5951-1.6698zM2.371 11.8765c-.7435-2.4358-1.1779-4.8851-1.2123-5.5719-.1086-2.1714.4171-3.6829 1.5623-4.4927 1.8367-1.2986 4.8398-.5408 6.108-.13-.0032.0032-.0066.0061-.0098.0094-2.0238 2.044-1.9758 5.536-1.9708 5.7495-.0002.0823.0066.1989.0162.3593.0348.5873.0996 1.6804-.0735 2.9184-.1609 1.1504.1937 2.2764.9728 3.0892.0806.0841.1648.1631.2518.2374-.3468.3714-1.1004 1.1926-1.9025 2.1576-.5677.6825-.9597.5517-1.0886.5087-.3919-.1307-.813-.5871-1.2381-1.3223-.4796-.839-.9635-2.0317-1.4155-3.5126zm6.0072 5.0871c-.1711-.0428-.3271-.1132-.4322-.1772.0889-.0394.2374-.0902.4833-.1409 1.2833-.2641 1.4815-.4506 1.9143-1.0002.0992-.126.2116-.2687.3673-.4426a.3549.3549 0 0 0 .0737-.1298c.1708-.1513.2724-.1099.4369-.0417.156.0646.3078.26.3695.4752.0291.1016.0619.2945-.0452.4444-.9043 1.2658-2.2216 1.2494-3.1676 1.0128zm2.094-3.988-.0525.141c-.133.3566-.2567.6881-.3334 1.003-.6674-.0021-1.3168-.2872-1.8105-.8024-.6279-.6551-.9131-1.5664-.7825-2.5004.1828-1.3079.1153-2.4468.079-3.0586-.005-.0857-.0095-.1607-.0122-.2199.2957-.2621 1.6659-.9962 2.6429-.7724.4459.1022.7176.4057.8305.928.5846 2.7038.0774 3.8307-.3302 4.7363-.084.1866-.1633.3629-.2311.5454zm7.3637 4.5725c-.0169.1768-.0358.376-.0618.5959l-.146.4383a.3547.3547 0 0 0-.0182.1077c-.0059.4747-.054.6489-.115.8693-.0634.2292-.1353.4891-.1794 1.0575-.11 1.4143-.8782 2.2267-2.4172 2.5565-1.5155.3251-1.7843-.4968-2.0212-1.2217a6.5824 6.5824 0 0 0-.0769-.2266c-.2154-.5858-.1911-1.4119-.1574-2.5551.0165-.5612-.0249-1.9013-.3302-2.6462.0044-.2932.0106-.5909.019-.8918a.3529.3529 0 0 0-.0153-.1126 1.4927 1.4927 0 0 0-.0439-.208c-.1226-.4283-.4213-.7866-.7797-.9351-.1424-.059-.4038-.1672-.7178-.0869.067-.276.1831-.5875.309-.9249l.0529-.142c.0595-.16.134-.3257.213-.5012.4265-.9476 1.0106-2.2453.3766-5.1772-.2374-1.0981-1.0304-1.6343-2.2324-1.5098-.7207.0746-1.3799.3654-1.7088.5321a5.6716 5.6716 0 0 0-.1958.1041c.0918-1.1064.4386-3.1741 1.7357-4.4823a4.0306 4.0306 0 0 1 .3033-.276.3532.3532 0 0 0 .1447-.0644c.7524-.5706 1.6945-.8506 2.802-.8325.4091.0067.8017.0339 1.1742.081 1.939.3544 3.2439 1.4468 4.0359 2.3827.8143.9623 1.2552 1.9315 1.4312 2.4543-1.3232-.1346-2.2234.1268-2.6797.779-.9926 1.4189.543 4.1729 1.2811 5.4964.1353.2426.2522.4522.2889.5413.2403.5825.5515.9713.7787 1.2552.0696.087.1372.1714.1885.245-.4008.1155-1.1208.3825-1.0552 1.717-.0123.1563-.0423.4469-.0834.8148-.0461.2077-.0702.4603-.0994.7662zm.8905-1.6211c-.0405-.8316.2691-.9185.5967-1.0105a2.8566 2.8566 0 0 0 .135-.0406 1.202 1.202 0 0 0 .1342.103c.5703.3765 1.5823.4213 3.0068.1344-.2016.1769-.5189.3994-.9533.6011-.4098.1903-1.0957.333-1.7473.3636-.7197.0336-1.0859-.0807-1.1721-.151zm.5695-9.2712c-.0059.3508-.0542.6692-.1054 1.0017-.055.3576-.112.7274-.1264 1.1762-.0142.4368.0404.8909.0932 1.3301.1066.887.216 1.8003-.2075 2.7014a3.5272 3.5272 0 0 1-.1876-.3856c-.0527-.1276-.1669-.3326-.3251-.6162-.6156-1.1041-2.0574-3.6896-1.3193-4.7446.3795-.5427 1.3408-.5661 2.1781-.463zm.2284 7.0137a12.3762 12.3762 0 0 0-.0853-.1074l-.0355-.0444c.7262-1.1995.5842-2.3862.4578-3.4385-.0519-.4318-.1009-.8396-.0885-1.2226.0129-.4061.0666-.7543.1185-1.0911.0639-.415.1288-.8443.1109-1.3505.0134-.0531.0188-.1158.0118-.1902-.0457-.4855-.5999-1.938-1.7294-3.253-.6076-.7073-1.4896-1.4972-2.6889-2.0395.5251-.1066 1.2328-.2035 2.0244-.1859 2.0515.0456 3.6746.8135 4.8242 2.2824a.908.908 0 0 1 .0667.1002c.7231 1.3556-.2762 6.2751-2.9867 10.5405zm-8.8166-6.1162c-.025.1794-.3089.4225-.6211.4225a.5821.5821 0 0 1-.0809-.0056c-.1873-.026-.3765-.144-.5059-.3156-.0458-.0605-.1203-.178-.1055-.2844.0055-.0401.0261-.0985.0925-.1488.1182-.0894.3518-.1226.6096-.0867.3163.0441.6426.1938.6113.4186zm7.9305-.4114c.0111.0792-.049.201-.1531.3102-.0683.0717-.212.1961-.4079.2232a.5456.5456 0 0 1-.075.0052c-.2935 0-.5414-.2344-.5607-.3717-.024-.1765.2641-.3106.5611-.352.297-.0414.6111.0088.6356.1851z",hex:"4169E1"},B0={path:"M4.928 1.825c-1.09.553-1.09.64-.07 1.78 5.655 6.295 7.004 7.782 7.107 7.782.139.017 7.971-8.542 8.058-8.801.034-.07-.208-.312-.519-.536-.415-.312-.864-.433-1.712-.467-1.59-.104-2.144.242-4.115 2.455-.899 1.003-1.66 1.833-1.66 1.833-.017 0-.76-.813-1.642-1.798S8.473 2.1 8.127 1.91c-.796-.45-2.421-.484-3.2-.086zM1.297 4.367C.45 4.695 0 5.007 0 5.248c0 .121 1.331 1.678 2.94 3.459 1.625 1.78 2.939 3.268 2.939 3.302 0 .035-1.331 1.522-2.94 3.303C1.314 17.11.017 18.683.035 18.822c.086.467 1.504 1.055 2.541 1.055 1.678-.018 2.058-.312 5.603-4.202 1.78-1.954 3.233-3.614 3.233-3.666 0-.069-1.435-1.694-3.199-3.63-2.3-2.508-3.423-3.632-3.96-3.874-.812-.398-2.126-.467-2.956-.138zm18.467.12c-.502.26-1.764 1.505-3.943 3.891-1.763 1.937-3.199 3.562-3.199 3.631 0 .07 1.453 1.712 3.234 3.666 3.544 3.89 3.925 4.184 5.602 4.202 1.038 0 2.455-.588 2.542-1.055.017-.156-1.28-1.712-2.905-3.493-1.608-1.78-2.94-3.285-2.94-3.32 0-.034 1.332-1.539 2.94-3.32C22.72 6.91 24.017 5.352 24 5.214c-.087-.45-1.366-.968-2.473-1.038-.795-.034-1.21.035-1.763.312zM7.954 16.973c-2.144 2.369-3.908 4.374-3.943 4.46-.034.07.208.312.52.537.414.311.864.432 1.711.467 1.574.103 2.161-.26 4.15-2.508.864-.968 1.608-1.78 1.625-1.78s.761.812 1.643 1.798c2.023 2.248 2.559 2.576 4.132 2.49.848-.035 1.297-.156 1.712-.467.311-.225.553-.467.519-.536-.087-.26-7.92-8.819-8.058-8.801-.069 0-1.867 1.954-4.011 4.34z",hex:"E57000"},P0={path:"M11.911 23.994c-1.31 0-2.605-.232-3.831-.705-3.4-1.024-6.2-3.865-7.433-7.58-1.23-3.708-.685-7.654 1.459-10.554C4.062 2.038 7.677.094 11.742.008c4.064-.079 7.758 1.703 9.882 4.785a12.066 12.066 0 0 1 2.369 7.145c.138 3.733-1.75 7.368-5.052 9.728-2.147 1.535-4.61 2.328-7.03 2.328zm.11-22.314c-.081 0-.162 0-.244.002-3.5.074-6.599 1.725-8.29 4.415-1.856 2.516-2.31 5.893-1.25 9.086 1.06 3.197 3.448 5.636 6.386 6.523 3.025 1.165 6.496.633 9.345-1.402 2.847-2.035 4.473-5.144 4.351-8.318v-.032c0-2.214-.73-4.41-2.055-6.185-1.78-2.58-4.84-4.09-8.243-4.09zM9.406 20.246v-4.578a2.663 2.663 0 0 1-.952.863 2.573 2.573 0 0 1-1.29.344c-1.016 0-1.893-.444-2.63-1.33-.731-.887-1.097-2.102-1.097-3.646 0-.939.148-1.781.444-2.527.301-.746.734-1.309 1.299-1.69A3.26 3.26 0 0 1 7.052 7.1c1.058 0 1.891.487 2.5 1.46v-1.25h1.306v12.935H9.406zm-4.477-8.285c0 1.203.232 2.108.694 2.711.463.6 1.016.9 1.662.9.619 0 1.15-.286 1.597-.855.446-.576.67-1.447.67-2.615 0-1.245-.237-2.18-.71-2.81-.468-.627-1.02-.941-1.654-.941-.63 0-1.164.293-1.605.88-.435.581-.654 1.491-.654 2.73m9.55 4.702h-1.346V3.755h1.452v4.604c.613-.84 1.395-1.258 2.347-1.258.526 0 1.024.117 1.492.351.464.222.864.558 1.161.978.307.416.546.922.718 1.514.172.593.258 1.227.258 1.902 0 1.603-.363 2.841-1.088 3.716-.727.874-1.598 1.312-2.614 1.312-1.011 0-1.804-.46-2.379-1.382v1.17m-.016-4.746c0 1.122.14 1.932.42 2.432.456.815 1.074 1.223 1.854 1.223.635 0 1.183-.3 1.646-.898.462-.604.693-1.503.693-2.695 0-1.22-.224-2.122-.67-2.703-.44-.58-.975-.872-1.605-.872-.634 0-1.182.303-1.645.907-.463.6-.694 1.468-.694 2.607",hex:"2F67BA"},E0={path:"M5.274 0C3.189.039 1.19 1.547 1.19 4.705l.184 14.518c0 1.47 1.103 2.205 2.573 2.021L3.764 3.786c0-1.654.919-1.838 2.022-1.103l14.7 8.27c1.103.734 1.655 1.47 1.838 2.756.92-1.654.552-4.043-1.286-5.33L7.991.846A4.559 4.559 0 0 0 5.274.001zm1.982 6.91-.184 10.107 9.004-5.146Zm13.598 6.064-15.068 8.82c-.92.552-2.022.736-3.124.368.918 1.47 3.307 2.389 5.145 1.47l12.68-7.35c1.102-.736 1.286-2.022.367-3.308z",hex:"FFCB3D"},S0={path:"M21.212 4.282c1.851 2.204 2.777 4.776 2.777 7.718 0 2.848-.867 5.344-2.602 7.489a934.355 934.355 0 0 1-2.101-2.095c-1.477-1.477-1.792-3.293-1.792-5.278 0-2.224.127-3.486 1.577-4.935l2.478-2.478a13.209 13.209 0 0 0-.337-.421Zm-17.7 16.193C1.708 18.678.6 16.59.188 14.213A11.84 11.84 0 0 1 .011 12c0-.28.006-.548.017-.802 0-.026.007-.052.022-.078.153-2.601 1.076-4.889 2.767-6.865-.108.127-.214.256-.316.387 0 0 1.351 1.346 2.329 2.323 1.408 1.409 1.726 3.215 1.726 5.151 0 1.985-.249 3.762-1.781 5.295-1.035 1.035-2.119 2.124-2.119 2.124.112.136.229.271.349.404.029-.027 1.297-1.348 2.123-2.175 1.638-1.637 1.928-3.528 1.928-5.648 0-2.072-.365-3.997-1.873-5.504a620.045 620.045 0 0 0-2.366-2.357c.168-.196.342-.388.523-.576l3.117 3.106-.194.195 1.903 1.898.547-.549L6.81 6.432l-.196.196L3.495 3.52c.01-.009.436-.416.643-.597.009.011 2.28 2.283 2.28 2.283 1.538 1.537 3.5 1.955 5.621 1.955 2.18 0 4.134-.442 5.731-2.038.907-.908 2.153-2.149 2.162-2.16.17.151.491.461.56.528l.013.013-3.111 3.028-.001.002-.197-.194-1.876 1.903.552.543 1.875-1.903-.197-.194 3.109-3.026c.193.203.377.41.553.619-.03.025-2.495 2.546-2.495 2.546-1.556 1.556-1.723 2.9-1.723 5.288 0 2.121.361 4.054 1.939 5.632a576.91 576.91 0 0 0 2.133 2.124c-.183.208-.599.645-.613.66l-3.066-3.174.195-.196-1.995-1.986-.546.549 1.995 1.986.195-.196 3.065 3.172c-.021.019-.385.362-.552.506-.01-.013-1.974-1.978-1.974-1.978-1.842-1.842-3.299-2.039-5.731-2.039-2.338 0-3.92.239-5.632 1.95-.944.944-2.078 2.085-2.089 2.099-.275-.23-.649-.594-.649-.594l3.019-3.024.199.192 1.854-1.925-.558-.538-1.854 1.926.199.191-3.016 3.022ZM12 8.672A3.33 3.33 0 0 0 8.672 12 3.33 3.33 0 0 0 12 15.328 3.33 3.33 0 0 0 15.328 12 3.33 3.33 0 0 0 12 8.672ZM4.52 2.6C6.665.867 9.162 0 12.011 0c2.88 0 5.394.88 7.541 2.639 0 0-1.215 1.209-2.136 2.13-1.496 1.496-3.334 1.892-5.377 1.892-1.985 0-3.829-.37-5.267-1.809L4.52 2.6Zm14.837 18.909a9.507 9.507 0 0 1-.342.256C16.994 23.255 14.659 24 12.011 24c-2.652 0-4.983-.745-6.993-2.235-.104-.074-.208-.15-.31-.227 0 0 1.096-1.101 2.053-2.058 1.602-1.602 3.09-1.804 5.278-1.804 2.28 0 3.651.166 5.377 1.892l1.941 1.941Z",hex:"2596BE"},D0={path:"M17.812 19.381A6.194 6.194 0 0 0 24 13.193c0-1.7-.723-3.352-1.958-4.515a6.01 6.01 0 0 0-6.005-5.955 5.98 5.98 0 0 0-2.731.656 5.985 5.985 0 0 0-4.12-1.635 6.011 6.011 0 0 0-6 5.743A6.224 6.224 0 0 0 0 12.917a6.225 6.225 0 0 0 6.706 6.2 6.426 6.426 0 0 0 5.508 3.14 6.395 6.395 0 0 0 5.347-2.881c.084.003.167.005.25.005zm-5.598 1.242A4.792 4.792 0 0 1 7.9 17.888l-.267-.562-.613.108a4.592 4.592 0 0 1-5.387-4.516A4.59 4.59 0 0 1 4.34 8.734l.506-.228-.026-.555a4.377 4.377 0 0 1 4.367-4.574c1.297 0 2.512.566 3.347 1.56l.47.56.609-.407a4.349 4.349 0 0 1 2.425-.734 4.378 4.378 0 0 1 4.364 4.632l-.025.416.322.265a4.612 4.612 0 0 1 1.669 3.524 4.561 4.561 0 0 1-5.14 4.518l-.554-.071-.267.49a4.764 4.764 0 0 1-4.192 2.493zm3.102-6.533.016-.007c.212-.091.288-.171.288-.393v-.278c0-.244-.14-.401-.37-.401h-.013l-.046.01a4.534 4.534 0 0 1-1.502.272c-.48 0-.954-.09-1.409-.27l-.013-.005-.052-.007c-.23 0-.37.157-.37.401v.278c0 .209.078.303.261.382l.02.009.02.008a3.91 3.91 0 0 0 1.544.32c.525 0 1.071-.107 1.626-.319zm-7.081-2.285c0-.224.116-.348.272-.38l1.501-.394-1.505-.395c-.156-.041-.268-.164-.268-.38v-.473c0-.207.124-.296.266-.296.046 0 .094.01.141.028l2.68.867c.203.068.315.231.315.455v.387c0 .224-.112.388-.316.456l-2.685.868a.437.437 0 0 1-.125.02c-.168 0-.276-.12-.276-.297v-.466z",hex:"000000"},G0={path:"M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z",hex:"FF0000"},T0={path:"m18.931 9.99-1.441-.601 1.717-.913a4.48 4.48 0 0 0 1.874-6.078 4.506 4.506 0 0 0-6.09-1.874L4.792 5.929a4.504 4.504 0 0 0-2.402 4.193 4.521 4.521 0 0 0 2.666 3.904c.036.012 1.442.6 1.442.6l-1.706.901a4.51 4.51 0 0 0-2.369 3.967A4.528 4.528 0 0 0 6.93 24c.725 0 1.437-.174 2.08-.508l10.21-5.406a4.494 4.494 0 0 0 2.39-4.192 4.525 4.525 0 0 0-2.678-3.904ZM9.597 15.19V8.824l6.007 3.184z",hex:"FF0000"};export{g0 as $,w as A,v0 as B,Z as C,F as D,P as E,E as F,R as G,I as H,N as I,_ as J,U as K,Q as L,a0 as M,c0 as N,Y as O,e0 as P,G as Q,l0 as R,k0 as S,M0 as T,T as U,W as V,z0 as W,X,x0 as Y,H as Z,m0 as _,T0 as a,V as a0,J as a1,s0 as a2,D as a3,S as a4,B as a5,y0 as a6,q as a7,L as a8,A as a9,p0 as aa,t0 as ab,h0 as ac,K as ad,r0 as ae,b as af,j as ag,$ as ah,n0 as ai,G0 as b,Z0 as c,H0 as d,j0 as e,b0 as f,w0 as g,V0 as h,F0 as i,P0 as j,S0 as k,E0 as l,L0 as m,f0 as n,C0 as o,B0 as p,u0 as q,q0 as r,D0 as s,A0 as t,C as u,O as v,i0 as w,o0 as x,d0 as y,f as z};
