<template>
  <div ref="el" class="co-chart" :style="{ height: height }"></div>
</template>

<script setup>
/**
 * ECharts 轻量封装。
 * - 自动初始化 / 销毁
 * - option 变化时增量更新
 * - 监听容器尺寸变化自适应
 */
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '300px' }
})

const el = ref(null)
let chart = null
let observer = null

function render() {
  if (!chart) return
  chart.setOption(props.option, true)
}

onMounted(() => {
  chart = echarts.init(el.value)
  render()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => chart && chart.resize())
    observer.observe(el.value)
  } else {
    window.addEventListener('resize', handleResize)
  }
})

function handleResize() {
  if (chart) chart.resize()
}

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  else window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose()
    chart = null
  }
})
</script>

<style scoped>
.co-chart {
  width: 100%;
}
</style>
