import { h } from "vue";
import {
  siAdguard,
  siCockpit,
  siDocker,
  siGitea,
  siGrafana,
  siHomeassistant,
  siJellyfin,
  siNginx,
  siNginxproxymanager,
  siOpenaigym,
  siOpenwrt,
  siPostgresql,
  siPortainer,
  siProxmox,
  siQbittorrent,
  siRadarr,
  siSonarr,
  siTermius,
  siYoutube,
  siYoutubeshorts,
} from "simple-icons";

export function createBrandIcon(icon) {
  const brandColor = `#${icon.hex}`;
  return (_props, { attrs }) =>
    h(
      "svg",
      {
        ...attrs,
        xmlns: "http://www.w3.org/2000/svg",
        viewBox: "0 0 24 24",
        fill: "currentColor",
        role: "img",
        "aria-hidden": "true",
        style: attrs.style
          ? [attrs.style, { color: brandColor }]
          : { color: brandColor },
      },
      [h("path", { d: icon.path })],
    );
}

export const BRAND_ICON_BY_KEY = {
  homeassistant: createBrandIcon(siHomeassistant),
  "home-assistant": createBrandIcon(siHomeassistant),
  ha: createBrandIcon(siHomeassistant),
  openwrt: createBrandIcon(siOpenwrt),
  adguard: createBrandIcon(siAdguard),
  proxmox: createBrandIcon(siProxmox),
  pve: createBrandIcon(siProxmox),
  grafana: createBrandIcon(siGrafana),
  gitea: createBrandIcon(siGitea),
  jellyfin: createBrandIcon(siJellyfin),
  jellyseerr: createBrandIcon(siJellyfin),
  sonarr: createBrandIcon(siSonarr),
  radarr: createBrandIcon(siRadarr),
  lidarr: createBrandIcon(siSonarr),
  readarr: createBrandIcon(siSonarr),
  bazarr: createBrandIcon(siSonarr),
  prowlarr: createBrandIcon(siSonarr),
  qbittorrent: createBrandIcon(siQbittorrent),
  qb: createBrandIcon(siQbittorrent),
  postgres: createBrandIcon(siPostgresql),
  postgresql: createBrandIcon(siPostgresql),
  docker: createBrandIcon(siDocker),
  dockge: createBrandIcon(siDocker),
  cockpit: createBrandIcon(siCockpit),
  npm: createBrandIcon(siNginxproxymanager),
  nginxproxymanager: createBrandIcon(siNginxproxymanager),
  "nginx-proxy-manager": createBrandIcon(siNginxproxymanager),
  nginx: createBrandIcon(siNginx),
  openai: createBrandIcon(siOpenaigym),
  ai: createBrandIcon(siOpenaigym),
  portainer: createBrandIcon(siPortainer),
  ytsync: createBrandIcon(siYoutubeshorts),
  youtube: createBrandIcon(siYoutube),
  youtubeshorts: createBrandIcon(siYoutubeshorts),
  termius: createBrandIcon(siTermius),
  termix: createBrandIcon(siTermius),
};
