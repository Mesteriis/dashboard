<template>
  <section class="ui-kit-section ui-html">
    <h2>Native HTML Catalog</h2>
    <p class="ui-kit-note">
      Full showcase of semantic tags and native form controls in one style namespace.
    </p>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-html-tags')"
        id="ui-node-html-tags"
        class="ui-html-card"
      >
        <header class="ui-html-card__head">
          <h3>Typography & Semantics</h3>
          <time datetime="2026-02-24">2026-02-24</time>
        </header>
        <h1>Heading H1</h1>
        <h2>Heading H2</h2>
        <h3>Heading H3</h3>
        <h4>Heading H4</h4>
        <h5>Heading H5</h5>
        <h6>Heading H6</h6>
        <p>
          Paragraph with <strong>strong</strong>, <em>em</em>, <small>small</small>,
          <mark>mark</mark>, <u>underline</u>, <s>strikethrough</s>, <del>del</del> and
          <ins>ins</ins>.
        </p>
        <p>
          <abbr title="Application Programming Interface">API</abbr> works with
          <dfn>domain terms</dfn>, <q cite="https://developer.mozilla.org/">inline quote</q>,
          <kbd>Ctrl</kbd> + <kbd>K</kbd>, <code>inline code</code>, <var>n</var>,
          <samp>OK</samp>, H<sub>2</sub>O, x<sup>2</sup>.
        </p>
        <blockquote cite="https://example.com">
          Build composable primitives first, then compose products from them.
          <cite>Design Notes</cite>
        </blockquote>
        <details>
          <summary>Details and summary</summary>
          <p>Disclosure widgets are fully styled inside the same UI namespace.</p>
        </details>
        <hr />
      </article>

      <article
        v-show="isNodeVisible('ui-node-html-table-lists')"
        id="ui-node-html-table-lists"
        class="ui-html-card"
      >
        <header class="ui-html-card__head">
          <h3>Lists & Table</h3>
          <data value="128">128 records</data>
        </header>
        <nav aria-label="Example nav">
          <a href="#" @click.prevent>Overview</a>
          <a href="#" @click.prevent>Services</a>
          <a href="#" @click.prevent>Settings</a>
        </nav>
        <ul>
          <li>Unordered item one</li>
          <li>Unordered item two</li>
        </ul>
        <ol>
          <li>Ordered item one</li>
          <li>Ordered item two</li>
        </ol>
        <dl>
          <dt>Latency</dt>
          <dd>Average response time in milliseconds.</dd>
          <dt>Uptime</dt>
          <dd>Availability over a rolling period.</dd>
        </dl>
        <pre><code>&lt;section class="panel"&gt;ui content&lt;/section&gt;</code></pre>
        <table>
          <caption>Native HTML Table</caption>
          <thead>
            <tr>
              <th scope="col">Service</th>
              <th scope="col">Status</th>
              <th scope="col">Latency</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">API Gateway</th>
              <td>Online</td>
              <td>42ms</td>
            </tr>
            <tr>
              <th scope="row">Billing</th>
              <td>Degraded</td>
              <td>137ms</td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td colspan="3">Total: 2 services</td>
            </tr>
          </tfoot>
        </table>
      </article>
    </div>

    <div class="ui-kit-grid cols-2">
      <article
        v-show="isNodeVisible('ui-node-html-media')"
        id="ui-node-html-media"
        class="ui-html-card"
      >
        <header class="ui-html-card__head">
          <h3>Media & Embeds</h3>
        </header>
        <figure>
          <picture>
            <source
              type="image/svg+xml"
              srcset="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='480' height='180'%3E%3Crect width='480' height='180' fill='%23071b2a'/%3E%3Ccircle cx='90' cy='90' r='60' fill='%232dd4bf' fill-opacity='0.45'/%3E%3Crect x='170' y='44' width='250' height='92' rx='14' fill='%23113a4f'/%3E%3C/svg%3E"
            />
            <img
              alt="Decorative dashboard tile"
              src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='480' height='180'%3E%3Crect width='480' height='180' fill='%23071b2a'/%3E%3Ccircle cx='90' cy='90' r='60' fill='%232dd4bf' fill-opacity='0.45'/%3E%3Crect x='170' y='44' width='250' height='92' rx='14' fill='%23113a4f'/%3E%3C/svg%3E"
            />
          </picture>
          <figcaption>Picture + source + img</figcaption>
        </figure>
        <svg viewBox="0 0 240 80" role="img" aria-label="Simple SVG sample">
          <rect x="4" y="4" width="232" height="72" rx="12" />
          <circle cx="50" cy="40" r="18" />
          <path d="M95 52 L132 26 L172 50" />
        </svg>
        <canvas ref="canvasRef" width="240" height="80">
          Canvas fallback text for unsupported browsers.
        </canvas>
        <iframe
          title="Inline iframe demo"
          srcdoc="<article><h4>Iframe content</h4><p>Scoped embed with own DOM.</p></article>"
        ></iframe>
        <progress :value="68" max="100">68%</progress>
        <meter min="0" max="100" low="40" high="75" optimum="90" :value="84">84</meter>
      </article>
      <UiKitHtmlFormCard v-show="isNodeVisible('ui-node-html-form-tags')" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import UiKitHtmlFormCard from "@/components/ui-kit/demo/UiKitHtmlFormCard.vue";

const props = withDefaults(
  defineProps<{
    activeNodeId?: string;
  }>(),
  {
    activeNodeId: "",
  },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);

function isNodeVisible(nodeId: string): boolean {
  if (!props.activeNodeId) return true;
  return props.activeNodeId === nodeId;
}

onMounted(() => {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  gradient.addColorStop(0, "#0b2435");
  gradient.addColorStop(1, "#2dd4bf");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = "rgba(2, 8, 14, 0.85)";
  ctx.fillRect(14, 14, canvas.width - 28, canvas.height - 28);

  ctx.fillStyle = "#8fd4e8";
  ctx.font = "12px monospace";
  ctx.fillText("canvas: native html element", 22, 46);
});
</script>
