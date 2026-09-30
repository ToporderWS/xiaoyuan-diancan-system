<template>
  <!--
    校园点餐 · 登录页左侧校园餐饮场景插画
    纯手绘 SVG（无位图背景、无远程 URL、非 AI 生成图）
    菜品照片使用项目本地 /public/dishes 下的真实菜品缩略图
    preserveAspectRatio=slice → 等比铺满容器并居中裁切；
    窗口 / 展示板 / 吊灯 / 前景人物等「主体」全部收在 x 84~676 安全区内，
    任何分辨率（含 1280×800）都不会把主体裁掉；雨棚、柜台、绿植属于可出血元素。
  -->
  <svg
    class="scene"
    viewBox="0 0 760 500"
    preserveAspectRatio="xMidYMid slice"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="sc-bg" x1="0" y1="0" x2="0.35" y2="1">
        <stop offset="0" stop-color="#FFFBF8" />
        <stop offset="1" stop-color="#FFF0E5" />
      </linearGradient>
      <linearGradient id="sc-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#FFE7CC" />
        <stop offset="1" stop-color="#FFCDA4" />
      </linearGradient>
      <linearGradient id="sc-floor" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#FBEAE0" />
        <stop offset="1" stop-color="#F3D7C3" />
      </linearGradient>
      <radialGradient id="sc-glow" cx="0.5" cy="0.5" r="0.5">
        <stop offset="0" stop-color="#FFC79B" stop-opacity="0.5" />
        <stop offset="1" stop-color="#FFC79B" stop-opacity="0" />
      </radialGradient>
      <clipPath id="sc-glass">
        <rect x="100" y="46" width="260" height="220" rx="6" />
      </clipPath>
      <clipPath id="sc-d1"><rect x="428" y="54" width="92" height="92" rx="15" /></clipPath>
      <clipPath id="sc-d2"><rect x="536" y="54" width="92" height="92" rx="15" /></clipPath>
      <clipPath id="sc-d3"><rect x="428" y="162" width="92" height="92" rx="15" /></clipPath>
      <clipPath id="sc-d4"><rect x="536" y="162" width="92" height="92" rx="15" /></clipPath>
    </defs>

    <!-- ============ 背景与地面 ============ -->
    <rect width="760" height="500" fill="url(#sc-bg)" />
    <circle cx="150" cy="60" r="196" fill="url(#sc-glow)" />
    <rect y="360" width="760" height="140" fill="url(#sc-floor)" />
    <ellipse cx="240" cy="432" rx="170" ry="34" fill="#FFF4E8" opacity="0.6" />
    <ellipse cx="200" cy="476" rx="124" ry="24" fill="#FFF8F0" opacity="0.5" />

    <!-- ============ 窗户：暖阳 + 校园远景 ============ -->
    <rect x="88" y="34" width="284" height="244" rx="14" fill="#FFFFFF" stroke="#F0DED4" stroke-width="2" />
    <g clip-path="url(#sc-glass)">
      <rect x="100" y="46" width="260" height="220" fill="url(#sc-sky)" />
      <circle cx="344" cy="84" r="25" fill="#FFB067" opacity="0.62" />
      <!-- 远景楼群（带窗格细节） -->
      <rect x="100" y="188" width="74" height="78" fill="#EABC98" opacity="0.8" />
      <rect x="180" y="212" width="54" height="54" fill="#E2AE88" opacity="0.75" />
      <rect x="240" y="198" width="60" height="68" fill="#EABC98" opacity="0.72" />
      <rect x="306" y="220" width="54" height="46" fill="#E2AE88" opacity="0.66" />
      <g fill="#FFF1E2" opacity="0.6">
        <rect x="108" y="198" width="10" height="12" /><rect x="126" y="198" width="10" height="12" />
        <rect x="108" y="220" width="10" height="12" /><rect x="126" y="220" width="10" height="12" />
        <rect x="144" y="198" width="10" height="12" /><rect x="144" y="220" width="10" height="12" />
        <rect x="188" y="222" width="9" height="11" /><rect x="204" y="222" width="9" height="11" />
        <rect x="188" y="240" width="9" height="11" /><rect x="204" y="240" width="9" height="11" />
        <rect x="248" y="208" width="10" height="12" /><rect x="266" y="208" width="10" height="12" />
        <rect x="248" y="230" width="10" height="12" /><rect x="266" y="230" width="10" height="12" />
        <rect x="284" y="208" width="10" height="12" /><rect x="284" y="230" width="10" height="12" />
        <rect x="314" y="228" width="9" height="11" /><rect x="330" y="228" width="9" height="11" />
      </g>
      <!-- 树丛 -->
      <circle cx="142" cy="178" r="27" fill="#D3BE97" opacity="0.9" />
      <circle cx="178" cy="190" r="18" fill="#C9B389" opacity="0.82" />
      <circle cx="282" cy="180" r="22" fill="#C9B389" opacity="0.75" />
      <circle cx="322" cy="192" r="14" fill="#D3BE97" opacity="0.72" />
    </g>
    <!-- 窗框分格 -->
    <rect x="226" y="46" width="8" height="220" fill="#FFFFFF" />
    <rect x="100" y="148" width="260" height="8" fill="#FFFFFF" />
    <!-- 窗台 + 小盆栽 -->
    <rect x="78" y="278" width="304" height="12" rx="6" fill="#F5E3D6" />
    <path d="M314 278 L348 278 L344 258 L318 258 Z" fill="#E7D6C8" />
    <g fill="#8FB69A">
      <ellipse cx="321" cy="246" rx="7" ry="16" transform="rotate(-24 321 246)" />
      <ellipse cx="332" cy="238" rx="7" ry="19" transform="rotate(-2 332 238)" />
      <ellipse cx="342" cy="248" rx="7" ry="15" transform="rotate(24 342 248)" />
    </g>

    <!-- ============ 斜射光带 ============ -->
    <polygon points="108,290 352,290 452,428 174,428" fill="#FFF4E8" opacity="0.5" />
    <polygon points="192,290 306,290 366,402 252,402" fill="#FFF9F0" opacity="0.38" />

    <!-- ============ 今日推荐展示板（真实菜品图） ============ -->
    <rect x="406" y="32" width="256" height="256" rx="24" fill="#DFC7B8" opacity="0.5" />
    <rect x="400" y="26" width="256" height="256" rx="24" fill="#FFFFFF" stroke="#F0DFD5" stroke-width="2" />
    <g>
      <image href="/dishes/dish-1.jpg" x="428" y="54" width="92" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#sc-d1)" />
      <image href="/dishes/dish-2.jpg" x="536" y="54" width="92" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#sc-d2)" />
      <image href="/dishes/dish-3.jpg" x="428" y="162" width="92" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#sc-d3)" />
      <image href="/dishes/dish-4.jpg" x="536" y="162" width="92" height="92" preserveAspectRatio="xMidYMid slice" clip-path="url(#sc-d4)" />
    </g>

    <!-- ============ 吊灯 ============ -->
    <g stroke="#E2C9B9" stroke-width="2">
      <line x1="150" y1="0" x2="150" y2="150" />
      <line x1="336" y1="0" x2="336" y2="126" />
    </g>
    <ellipse cx="150" cy="168" rx="30" ry="11" fill="#FFD9AE" opacity="0.75" />
    <path d="M126 152 L174 152 L165 128 L135 128 Z" fill="#FFFFFF" stroke="#F0DFD5" stroke-width="2" />
    <rect x="132" y="124" width="36" height="6" rx="3" fill="#E8453C" />
    <ellipse cx="336" cy="144" rx="26" ry="9" fill="#FFD9AE" opacity="0.6" />
    <path d="M315 130 L357 130 L349 108 L323 108 Z" fill="#FFFFFF" stroke="#F0DFD5" stroke-width="2" />
    <rect x="320" y="104" width="32" height="6" rx="3" fill="#E8453C" />

    <!-- ============ 档口雨棚（品牌红 + 品牌语 + 扇贝边，可出血） ============ -->
    <rect x="14" y="296" width="732" height="36" rx="10" fill="#E8453C" />
    <rect x="14" y="296" width="732" height="8" rx="4" fill="#F4675E" />
    <g fill="#E8453C">
      <circle cx="36" cy="332" r="22" /><circle cx="80" cy="332" r="22" />
      <circle cx="124" cy="332" r="22" /><circle cx="168" cy="332" r="22" />
      <circle cx="212" cy="332" r="22" /><circle cx="256" cy="332" r="22" />
      <circle cx="300" cy="332" r="22" /><circle cx="344" cy="332" r="22" />
      <circle cx="388" cy="332" r="22" /><circle cx="432" cy="332" r="22" />
      <circle cx="476" cy="332" r="22" /><circle cx="520" cy="332" r="22" />
      <circle cx="564" cy="332" r="22" /><circle cx="608" cy="332" r="22" />
      <circle cx="652" cy="332" r="22" /><circle cx="696" cy="332" r="22" />
      <circle cx="740" cy="332" r="22" />
    </g>
    <text
      x="380" y="321" text-anchor="middle" fill="#FFFFFF"
      font-size="17" font-weight="600" letter-spacing="2"
    >美味校园餐 · 从这里开始</text>

    <!-- ============ 打饭档口柜台（可出血） ============ -->
    <rect x="60" y="338" width="640" height="70" rx="12" fill="#FFFFFF" stroke="#F0DFD5" stroke-width="2" />
    <rect x="60" y="338" width="640" height="11" rx="6" fill="#F5E6DA" />
    <rect x="60" y="394" width="640" height="14" rx="7" fill="#F2E4D8" />
    <!-- 餐盘与菜品 -->
    <g>
      <rect x="96" y="356" width="120" height="32" rx="9" fill="#FBF4EF" stroke="#EEDCD2" stroke-width="2" />
      <ellipse cx="156" cy="372" rx="42" ry="11" fill="#D9902F" />
      <rect x="230" y="356" width="120" height="32" rx="9" fill="#FBF4EF" stroke="#EEDCD2" stroke-width="2" />
      <ellipse cx="290" cy="372" rx="42" ry="11" fill="#C8463D" />
      <rect x="364" y="356" width="120" height="32" rx="9" fill="#FBF4EF" stroke="#EEDCD2" stroke-width="2" />
      <ellipse cx="424" cy="372" rx="42" ry="11" fill="#BC7726" />
      <rect x="498" y="356" width="120" height="32" rx="9" fill="#FBF4EF" stroke="#EEDCD2" stroke-width="2" />
      <ellipse cx="558" cy="372" rx="42" ry="11" fill="#6F9C7C" />
      <!-- 蒸笼 -->
      <rect x="632" y="348" width="80" height="11" rx="5" fill="#E6D6C6" />
      <rect x="638" y="359" width="68" height="11" rx="5" fill="#DDCBB8" />
      <rect x="644" y="370" width="56" height="11" rx="5" fill="#D4C0AC" />
      <ellipse cx="672" cy="348" rx="40" ry="8" fill="#F4EAE0" />
    </g>

    <!-- ============ 前景：两位学生背影（暖色剪影，低饱和不抢视觉） ============ -->
    <g>
      <circle cx="272" cy="412" r="16" fill="#C6A692" />
      <path d="M248 460c0-14 10.7-24 24-24s24 10 24 24v14h-48z" fill="#E3AE9C" />
    </g>
    <rect x="256" y="472" width="32" height="13" rx="6" fill="#C9AFA0" />
    <g>
      <circle cx="364" cy="424" r="13" fill="#BCA48F" />
      <path d="M344 464c0-11 9-19.5 20-19.5s20 8.5 20 19.5v11h-40z" fill="#A6C1AE" />
    </g>
    <rect x="350" y="473" width="28" height="11" rx="5" fill="#BBA898" />

    <!-- ============ 绿植（左，可出血） ============ -->
    <g>
      <path d="M34 434 L94 434 L87 500 L41 500 Z" fill="#E5D7CB" />
      <rect x="30" y="424" width="68" height="15" rx="7" fill="#DCCBBC" />
      <g fill="#8FB69A">
        <ellipse cx="44" cy="392" rx="9" ry="24" transform="rotate(-32 44 392)" />
        <ellipse cx="66" cy="378" rx="9" ry="28" transform="rotate(-8 66 378)" />
        <ellipse cx="88" cy="394" rx="9" ry="24" transform="rotate(28 88 394)" />
      </g>
      <g fill="#7CA487">
        <ellipse cx="56" cy="400" rx="8" ry="19" transform="rotate(-18 56 400)" />
        <ellipse cx="76" cy="404" rx="8" ry="19" transform="rotate(18 76 404)" />
      </g>
    </g>

    <!-- ============ 绿植（右下，越过画布形成景深） ============ -->
    <g fill="#7FA688" opacity="0.95">
      <ellipse cx="712" cy="452" rx="26" ry="76" transform="rotate(26 712 452)" />
      <ellipse cx="762" cy="486" rx="30" ry="90" transform="rotate(16 762 486)" />
      <ellipse cx="678" cy="512" rx="22" ry="60" transform="rotate(40 678 512)" />
    </g>
  </svg>
</template>

<script setup>
defineOptions({ name: 'LoginScene' })
</script>

<style scoped>
.scene {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
