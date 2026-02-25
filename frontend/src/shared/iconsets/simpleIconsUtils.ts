export interface BuiltinIconPickerOption {
  id: string;
  label: string;
  pack?: string;
  keywords?: string[];
  preview?: string;
  svgPath?: string;
  svgBody?: string;
  svgViewBox?: string;
  svgColor?: string;
}

export interface BuiltinIconPickerSet {
  id: string;
  label: string;
  options: BuiltinIconPickerOption[];
}

export interface SimpleIconLike {
  title: string;
  slug: string;
  path: string;
  hex: string;
}

const SIMPLE_INFRA_HINTS = [
  "docker",
  "kubernetes",
  "k8s",
  "linux",
  "ubuntu",
  "debian",
  "nginx",
  "apache",
  "traefik",
  "postgres",
  "mysql",
  "mariadb",
  "mongodb",
  "redis",
  "sqlite",
  "oracle",
  "grafana",
  "prometheus",
  "elastic",
  "kibana",
  "logstash",
  "jenkins",
  "ansible",
  "terraform",
  "helm",
  "nomad",
  "vault",
  "consul",
  "rabbitmq",
  "kafka",
  "nats",
  "cloud",
  "aws",
  "azure",
  "gcp",
  "openstack",
  "vmware",
  "proxmox",
  "wireguard",
  "openvpn",
  "tailscale",
  "pfsense",
  "opnsense",
  "portainer",
  "ceph",
  "minio",
  "netdata",
  "unix",
  "bash",
  "gnubash",
  "shell",
  "terminal",
] as const;

export function isSimpleIconLike(value: unknown): value is SimpleIconLike {
  if (!value || typeof value !== "object") return false;

  const candidate = value as Partial<SimpleIconLike>;
  return (
    typeof candidate.title === "string" &&
    typeof candidate.slug === "string" &&
    typeof candidate.path === "string" &&
    typeof candidate.hex === "string"
  );
}

export function uniqueKeywords(words: string[]): string[] {
  return Array.from(new Set(words.map((word) => word.trim().toLowerCase()).filter(Boolean)));
}

function splitWords(source: string): string[] {
  return source
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
}

export function isInfraSlug(slug: string): boolean {
  const normalized = slug.toLowerCase();
  return SIMPLE_INFRA_HINTS.some((hint) => normalized.includes(hint));
}

export function isInfraIcon(icon: Pick<SimpleIconLike, "slug" | "title">): boolean {
  const haystack = `${icon.slug} ${icon.title}`.toLowerCase();
  return SIMPLE_INFRA_HINTS.some((hint) => haystack.includes(hint));
}

export function simpleToOption(icon: SimpleIconLike, pack: string): BuiltinIconPickerOption {
  return {
    id: `simple:${icon.slug}`,
    label: icon.title,
    pack,
    keywords: uniqueKeywords([
      ...splitWords(icon.slug),
      ...splitWords(icon.title),
      "service",
      "infrastructure",
      pack,
    ]),
    svgPath: icon.path,
    svgViewBox: "0 0 24 24",
    svgColor: `#${icon.hex}`,
  };
}

export function basicIcon(config: {
  id: string;
  label: string;
  svgPath: string;
  keywords: string[];
}): BuiltinIconPickerOption {
  return {
    id: `basic:${config.id}`,
    label: config.label,
    pack: "basic-ui",
    keywords: uniqueKeywords([...config.keywords, "basic", "ui"]),
    svgPath: config.svgPath,
    svgViewBox: "0 0 24 24",
    svgColor: "#CFDEEB",
  };
}
