<template>
  <v-app>
    <v-layout class="app-shell">
      <v-navigation-drawer
        v-if="authenticated"
        v-model="drawer"
        :rail="rail"
        width="248"
        class="nav"
      >
        <div class="brand">
          <v-icon icon="mdi-bike" size="28" />
          <span v-if="!rail">Cowboy Dashboard</span>
        </div>
        <v-list density="compact" nav>
          <v-list-item
            v-for="item in navItems"
            :key="item.value"
            :active="view === item.value"
            :prepend-icon="item.icon"
            :title="item.title"
            @click="view = item.value"
          />
        </v-list>
        <template #append>
          <div class="nav-actions">
            <v-btn
              :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
              variant="text"
              size="small"
              @click="rail = !rail"
            />
            <v-btn icon="mdi-logout" variant="text" size="small" @click="logout" />
          </div>
        </template>
      </v-navigation-drawer>

      <v-main>
        <section v-if="!authenticated" class="login-screen">
          <div class="login-panel">
            <div class="login-copy">
              <div class="route-lines" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <div class="mark"><v-icon icon="mdi-bike" /></div>
              <h1>Cowboy Dashboard</h1>
            </div>
            <v-form class="login-form" @submit.prevent="login">
              <div class="form-head">
                <h2>{{ t('signIn') }}</h2>
                <p>{{ t('credentialNotice') }}</p>
              </div>
              <label class="input-field">
                <span>{{ t('email') }}</span>
                <input
                  v-model="email"
                  type="email"
                  autocomplete="username"
                  placeholder="name@example.com"
                />
              </label>
              <label class="input-field">
                <span>{{ t('password') }}</span>
                <input
                  v-model="password"
                  type="password"
                  autocomplete="current-password"
                  :placeholder="t('passwordPlaceholder')"
                />
              </label>
              <v-alert v-if="error" type="error" density="compact" variant="tonal">{{ error }}</v-alert>
              <v-btn
                type="button"
                color="primary"
                size="large"
                block
                :loading="loading"
                prepend-icon="mdi-login"
                @click="login"
              >
                {{ t('loginButton') }}
              </v-btn>
            </v-form>
          </div>
        </section>

        <section v-else class="workspace">
          <header class="topbar">
            <div>
              <h1>{{ currentTitle }}</h1>
              <p>{{ subtitle }}</p>
            </div>
            <div class="topbar-actions">
              <div class="profile-chip">
                <div class="profile-avatar" aria-hidden="true">
                  <img
                    v-if="showProfileAvatar"
                    :src="profileAvatarUrl"
                    :alt="profileName"
                    @error="profileAvatarFailed = true"
                  />
                  <span v-else>{{ profileInitials }}</span>
                </div>
                <div class="profile-text">
                  <strong>{{ profileName }}</strong>
                  <span>{{ me.email || me.uid || 'Cowboy' }}</span>
                </div>
              </div>
              <label class="language-select">
                <span>{{ t('language') }}</span>
                <select v-model="language">
                  <option v-for="option in languageOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </label>
              <v-btn
                color="primary"
                variant="flat"
                prepend-icon="mdi-sync"
                :loading="syncing"
                class="action-btn"
                @click="syncMissingTrips"
              >
                {{ t('startSync') }}
              </v-btn>
              <v-menu>
                <template #activator="{ props }">
                  <v-btn v-bind="props" icon="mdi-dots-vertical" variant="text" />
                </template>
                <v-list density="compact">
                  <v-list-item prepend-icon="mdi-database-sync" :title="t('syncAllTrips')" @click="syncAllTrips" />
                  <v-list-item prepend-icon="mdi-refresh" :title="t('reload')" @click="refreshAll" />
                </v-list>
              </v-menu>
            </div>
          </header>

          <v-alert v-if="error" type="error" density="compact" variant="tonal" class="mb-4">{{ error }}</v-alert>

          <div class="status-strip">
            <div class="status-pill">
              <v-icon icon="mdi-battery" />
              <span>{{ t('battery') }}</span>
              <strong>{{ batteryLabel }}</strong>
            </div>
            <div class="status-pill">
              <v-icon icon="mdi-map-marker-distance" />
              <span>{{ t('range') }}</span>
              <strong>{{ rangeLabel }}</strong>
            </div>
            <div class="status-pill">
              <v-icon icon="mdi-bike" />
              <span>Bike</span>
              <strong>{{ bikeName }}</strong>
            </div>
            <div class="status-pill">
              <v-icon icon="mdi-clock-outline" />
              <span>{{ t('signal') }}</span>
              <strong>{{ formatDate(bike?.seen_at || bike?.battery_state_of_charge_updated_at) }}</strong>
            </div>
          </div>

          <div v-if="view === 'dashboard'" class="dashboard">
            <section class="controls-card dashboard-controls-card">
              <div class="range-bar">
                <label class="mini-field">
                  <span>{{ t('from') }}</span>
                  <input v-model="dateFrom" type="date" @input="clearDrilldownForRange" />
                </label>
                <label class="mini-field">
                  <span>{{ t('to') }}</span>
                  <input v-model="dateTo" type="date" @input="clearDrilldownForRange" />
                </label>
                <v-btn
                  variant="tonal"
                  prepend-icon="mdi-refresh"
                  class="action-btn"
                  @click="resetFilters"
                >
                  {{ t('reset') }}
                </v-btn>
              </div>
            </section>

            <div class="dashboard-grid">
              <section class="bike-panel bike-hero">
                <div class="panel-title">
                  <v-icon icon="mdi-bike" />
                  <div>
                    <h2>{{ bikeName }}</h2>
                    <p>{{ bikeModel }}</p>
                  </div>
                </div>
                <div class="battery-row">
                  <v-progress-circular
                    :model-value="batteryPercent"
                    :color="batteryColor"
                    size="132"
                    width="13"
                  >
                    <strong>{{ batteryLabel }}</strong>
                  </v-progress-circular>
                  <dl class="bike-facts">
                    <dt>{{ t('range') }}</dt>
                    <dd>{{ formatNullableKm(bike?.autonomy) }}</dd>
                    <dt>PCB-SoC</dt>
                    <dd>{{ formatPercent(bike?.pcb_battery_state_of_charge) }}</dd>
                    <dt>{{ t('batteryLevel') }}</dt>
                    <dd>{{ formatDate(bike?.battery_state_of_charge_updated_at) }}</dd>
                    <dt>{{ t('batteryInserted') }}</dt>
                    <dd>{{ bike?.battery_inserted === false ? t('no') : t('yes') }}</dd>
                    <dt>{{ t('lastSignal') }}</dt>
                    <dd>{{ formatDate(bike?.seen_at || bike?.battery_state_of_charge_updated_at) }}</dd>
                    <dt>Firmware</dt>
                    <dd>{{ bike?.firmware_version || '-' }}</dd>
                  </dl>
                </div>
              </section>

              <section class="sync-panel">
                <div class="panel-title">
                  <v-icon icon="mdi-database-sync-outline" />
                  <div>
                    <h2>Sync</h2>
                    <p>{{ subtitle }}</p>
                  </div>
                </div>
              <div class="sync-controls">
                  <label class="mini-field">
                    <span>{{ t('period') }}</span>
                    <select v-model.number="syncDays">
                      <option :value="400">{{ t('about12Months') }}</option>
                      <option :value="1000">{{ t('about3Years') }}</option>
                      <option :value="5000">{{ t('allTrips') }}</option>
                    </select>
                  </label>
                  <v-checkbox
                    v-model="syncFull"
                    hide-details
                    density="compact"
                    color="primary"
                    :label="t('fullRelist')"
                  />
                  <v-btn
                    color="primary"
                    variant="flat"
                    prepend-icon="mdi-sync"
                    :loading="syncing"
                    class="action-btn"
                    @click="runSync(syncFull)"
                  >
                    {{ syncFull ? t('relistAllTrips') : t('syncMissingTrips') }}
                  </v-btn>
                </div>
              </section>
            </div>

            <div class="metric-grid">
              <div class="metric">
                <span>{{ t('trips') }}</span>
                <strong>{{ selectedStats.tripCount }}</strong>
              </div>
              <div class="metric">
                <span>{{ t('routes') }}</span>
                <strong>{{ selectedStats.routeCount }}</strong>
              </div>
              <div class="metric">
                <span>{{ t('distance') }}</span>
                <strong>{{ formatKm(selectedStats.distanceKm) }}</strong>
              </div>
              <div class="metric">
                <span>{{ t('rideTime') }}</span>
                <strong>{{ formatDuration(selectedStats.durationS) }}</strong>
              </div>
              <div class="metric">
                <span>{{ t('average') }}</span>
                <small>{{ metricScopeLabel }}</small>
                <strong>{{ formatSpeed(selectedStats.averageSpeedKmh) }}</strong>
              </div>
              <div class="metric">
                <span>Human Power</span>
                <small>{{ metricScopeLabel }}</small>
                <strong>{{ formatWatts(selectedStats.averageUserPower) }}</strong>
              </div>
              <div class="metric">
                <span>Motor Power</span>
                <small>{{ metricScopeLabel }}</small>
                <strong>{{ formatWatts(selectedStats.averageMotorPower) }}</strong>
              </div>
              <div class="metric">
                <span>{{ t('co2Saved') }}</span>
                <strong>{{ formatGrams(selectedStats.co2Saved) }}</strong>
              </div>
            </div>
            <div class="chart-panel chart-panel-large">
              <div class="panel-title compact-title">
                <v-icon icon="mdi-chart-bar" />
                <div>
                  <h2>{{ chartTitle }}</h2>
                  <p>{{ chartHint }}</p>
                </div>
              </div>
              <apexchart
                height="320"
                type="bar"
                :options="chartOptions"
                :series="chartSeries"
                @data-point-selection="handleChartSelection"
              />
            </div>

            <section class="dashboard-map-panel">
              <div class="panel-title compact-title">
                <v-icon icon="mdi-map" />
                <div>
                  <h2>Heatmap</h2>
                  <p>{{ heatmapStatus }}</p>
                </div>
              </div>
              <div class="map-wrap dashboard-map-wrap">
                <div ref="mapEl" class="map"></div>
                <canvas ref="heatCanvasEl" class="heat-canvas"></canvas>
                <div class="map-controls compact-map-controls">
                  <v-btn-toggle v-model="mapMode" density="compact" mandatory>
                    <v-btn value="heatmap" prepend-icon="mdi-fire" class="mode-btn">Heatmap</v-btn>
                    <v-btn value="routes" prepend-icon="mdi-map-marker-path" class="mode-btn">{{ t('routes') }}</v-btn>
                  </v-btn-toggle>
                  <div class="map-toggle-group">
                    <span>Grid</span>
                    <div class="segmented-control three" role="group" :aria-label="t('heatmapGrid')">
                      <button
                        v-for="size in heatmapGridOptions"
                        :key="size"
                        type="button"
                        :class="['segment-button', { active: heatmapGrid === size }]"
                        @click="setHeatmapGrid(size)"
                      >
                        <span>{{ size }} m</span>
                      </button>
                    </div>
                  </div>
                  <div class="map-toggle-group">
                    <span>{{ t('display') }}</span>
                    <div class="segmented-control" role="group" :aria-label="t('heatmapDisplay')">
                      <button
                        type="button"
                        :class="['segment-button', { active: showFrequency }]"
                        @click="setHeatmapWeightMode('frequency')"
                      >
                        <v-icon icon="mdi-brightness-6" size="18" />
                        <span>{{ t('frequency') }}</span>
                      </button>
                      <button
                        type="button"
                        :class="['segment-button', { active: !showFrequency }]"
                        @click="setHeatmapWeightMode('plain')"
                      >
                        <v-icon icon="mdi-map-marker-path" size="18" />
                        <span>{{ t('plainRoute') }}</span>
                      </button>
                    </div>
                  </div>
                </div>
                <div v-if="heatmapBusy" class="map-busy">
                  <div class="loading-progress"><span /></div>
                  <strong>{{ t('drawingHeatmap') }}</strong>
                  <span>{{ heatmapStatus }}</span>
                </div>
                <div v-else-if="mapError" class="map-empty map-error">
                  <v-icon icon="mdi-alert-circle-outline" />
                  <span>{{ mapError }}</span>
                  <v-btn size="small" variant="tonal" @click="initMap">{{ t('redraw') }}</v-btn>
                </div>
                <div v-else-if="!roadFeatureCount" class="map-empty">
                  <v-icon icon="mdi-map-marker-off-outline" />
                  <span>{{ t('noRoutesForFilter') }}</span>
                </div>
                <div v-else class="heatmap-meta">
                  {{ roadRouteCount }} {{ t('routesLower') }} ·
                  {{ roadHeatmapData.properties?.stretches || 0 }} {{ t('segmentsLower') }} ·
                  max {{ roadHeatmapData.properties?.max_count || 0 }}x
                </div>
              </div>
            </section>

            <div class="details-grid">
              <section class="detail-panel">
                <div class="panel-title compact-title">
                  <v-icon icon="mdi-bicycle" />
                  <div>
                    <h2>{{ t('bike') }}</h2>
                    <p>{{ bikeModel }}</p>
                  </div>
                </div>
                <dl class="dense-facts">
                  <dt>{{ t('name') }}</dt><dd>{{ bikeName }}</dd>
                  <dt>{{ t('model') }}</dt><dd>{{ bikeModel }}</dd>
                  <dt>{{ t('color') }}</dt><dd>{{ bikeColor }}</dd>
                  <dt>SKU</dt><dd>{{ bike?.sku_code || bike?.sku?.code || '-' }}</dd>
                  <dt>Firmware</dt><dd>{{ bike?.firmware_version || '-' }}</dd>
                  <dt>Ride Mode</dt><dd>{{ bike?.last_ride_mode || bike?.settings?.default_ride_mode || '-' }}</dd>
                </dl>
              </section>

              <section class="detail-panel">
                <div class="panel-title compact-title">
                  <v-icon icon="mdi-shield-alert-outline" />
                  <div>
                    <h2>Status</h2>
                    <p>{{ t('statusSubtitle') }}</p>
                  </div>
                </div>
                <dl class="dense-facts">
                  <dt>{{ t('batterySoc') }}</dt><dd>{{ batteryLabel }}</dd>
                  <dt>PCB SoC</dt><dd>{{ formatPercent(bike?.pcb_battery_state_of_charge) }}</dd>
                  <dt>{{ t('batteryInserted') }}</dt><dd>{{ yesNo(bike?.battery_inserted) }}</dd>
                  <dt>{{ t('stolen') }}</dt><dd>{{ yesNo(bike?.stolen) }}</dd>
                  <dt>Crash</dt><dd>{{ yesNo(bike?.crashed) }}</dd>
                  <dt>{{ t('lastCrash') }}</dt><dd>{{ formatDate(bike?.last_crash_started_at) }}</dd>
                </dl>
              </section>

              <section class="detail-panel">
                <div class="panel-title compact-title">
                  <v-icon icon="mdi-map-marker-radius-outline" />
                  <div>
                    <h2>{{ t('location') }}</h2>
                    <p>{{ bike?.position?.source || 'Bike' }}</p>
                  </div>
                </div>
                <dl class="dense-facts">
                  <dt>Latitude</dt><dd>{{ formatCoordinate(bike?.position?.latitude) }}</dd>
                  <dt>Longitude</dt><dd>{{ formatCoordinate(bike?.position?.longitude) }}</dd>
                  <dt>{{ t('accuracy') }}</dt><dd>{{ formatMeters(bike?.position?.accuracy) }}</dd>
                  <dt>{{ t('type') }}</dt><dd>{{ bike?.position?.type || '-' }}</dd>
                  <dt>{{ t('received') }}</dt><dd>{{ formatDate(bike?.position?.received_at) }}</dd>
                  <dt>{{ t('signal') }}</dt><dd>{{ formatDate(bike?.seen_at) }}</dd>
                </dl>
              </section>
            </div>

            <div class="details-grid two-columns">
              <section class="detail-panel">
                <div class="panel-title compact-title">
                  <v-icon icon="mdi-battery-clock-outline" />
                  <div>
                    <h2>Autonomies</h2>
                    <p>{{ t('autonomiesSubtitle') }}</p>
                  </div>
                </div>
                <div class="autonomy-list">
                  <div v-for="item in bikeAutonomies" :key="item.ride_mode" class="autonomy-row">
                    <span>{{ formatRideMode(item.ride_mode) }}</span>
                    <strong>{{ formatNullableKm(item.full_battery_range) }}</strong>
                    <em>{{ item.calibrated ? t('calibrated') : t('notCalibrated') }}</em>
                  </div>
                  <div v-if="!bikeAutonomies.length" class="empty-inline">{{ t('noAutonomyData') }}</div>
                </div>
              </section>

              <section class="detail-panel">
                <div class="panel-title compact-title">
                  <v-icon icon="mdi-tune-variant" />
                  <div>
                    <h2>Features & Settings</h2>
                    <p>{{ t('featuresSubtitle') }}</p>
                  </div>
                </div>
                <div class="feature-grid">
                  <span v-for="feature in bikeFeatures" :key="feature.key" :class="['feature-pill', feature.value]">
                    {{ feature.label }}: {{ feature.value }}
                  </span>
                  <span v-for="setting in bikeSettings" :key="setting.key" class="feature-pill setting">
                    {{ setting.label }}: {{ setting.value }}
                  </span>
                </div>
              </section>
            </div>
          </div>

          <div v-if="view === 'heatmap'" class="map-view">
            <section class="controls-card heatmap-controls-card">
              <div class="panel-title compact-title">
                <v-icon icon="mdi-tune-variant" />
                <div>
                  <h2>{{ t('adjustHeatmap') }}</h2>
                  <p>{{ heatmapStatus }}</p>
                </div>
              </div>
              <div class="filter-bar">
              <label class="mini-field">
                <span>{{ t('syncPeriod') }}</span>
                <select v-model.number="syncDays">
                  <option :value="400">{{ t('about12Months') }}</option>
                  <option :value="1000">{{ t('about3Years') }}</option>
                  <option :value="5000">{{ t('allTrips') }}</option>
                </select>
              </label>
              <label class="mini-field">
                <span>{{ t('from') }}</span>
                <input v-model="dateFrom" type="date" @input="clearDrilldownForRange" />
              </label>
              <label class="mini-field">
                <span>{{ t('to') }}</span>
                <input v-model="dateTo" type="date" @input="clearDrilldownForRange" />
              </label>
              <label class="mini-field">
                <span>{{ t('year') }}</span>
                <select v-model="selectedYear" :disabled="hasDateRange">
                  <option value="">{{ t('allYears') }}</option>
                  <option v-for="year in availableYears" :key="year" :value="year">
                    {{ year }}
                  </option>
                </select>
              </label>
              <label class="mini-field">
                <span>{{ t('month') }}</span>
                <select v-model="selectedMonth" :disabled="!selectedYear || hasDateRange">
                  <option value="">{{ t('wholeYear') }}</option>
                  <option v-for="month in monthsInSelectedYear" :key="month.value" :value="month.value">
                    {{ month.label }}
                  </option>
                </select>
              </label>
              <label class="mini-field">
                <span>{{ t('day') }}</span>
                <select v-model="selectedDay" :disabled="!selectedMonth || hasDateRange">
                  <option value="">{{ t('wholeMonth') }}</option>
                  <option v-for="day in daysInSelectedMonth" :key="day.value" :value="day.value">
                    {{ day.label }}
                  </option>
                </select>
              </label>
              <div class="toggle-field grid-toggle-field">
                <span>Grid</span>
                <div class="segmented-control three" role="group" :aria-label="t('heatmapGrid')">
                  <button
                    v-for="size in heatmapGridOptions"
                    :key="size"
                    type="button"
                    :class="['segment-button', { active: heatmapGrid === size }]"
                    @click="setHeatmapGrid(size)"
                  >
                    <span>{{ size }} m</span>
                  </button>
                </div>
              </div>
              <div class="toggle-field heatmap-toggle-field">
                <span>{{ t('display') }}</span>
                <div class="segmented-control" role="group" :aria-label="t('heatmapDisplay')">
                  <button
                    type="button"
                    :class="['segment-button', { active: showFrequency }]"
                    @click="setHeatmapWeightMode('frequency')"
                  >
                    <v-icon icon="mdi-brightness-6" size="18" />
                    <span>{{ t('frequency') }}</span>
                  </button>
                  <button
                    type="button"
                    :class="['segment-button', { active: !showFrequency }]"
                    @click="setHeatmapWeightMode('plain')"
                  >
                    <v-icon icon="mdi-map-marker-path" size="18" />
                    <span>{{ t('plainRoute') }}</span>
                  </button>
                </div>
              </div>
              <div class="sync-button-group">
                <v-btn
                  color="primary"
                  variant="flat"
                  prepend-icon="mdi-database-sync-outline"
                  :loading="syncing"
                  class="action-btn"
                  @click="syncMissingTrips"
                >
                  {{ t('startSync') }}
                </v-btn>
                <v-btn
                  variant="tonal"
                  color="secondary"
                  prepend-icon="mdi-database-refresh-outline"
                  :loading="syncing"
                  class="action-btn"
                  @click="syncAllTrips"
                >
                  {{ t('relistAll') }}
                </v-btn>
              </div>
              <v-btn
                variant="tonal"
                color="primary"
                prepend-icon="mdi-filter-off-outline"
                class="action-btn"
                @click="resetFilters"
              >
                {{ t('reset') }}
              </v-btn>
              </div>
            </section>
            <div class="map-wrap">
              <div ref="mapEl" class="map"></div>
              <canvas ref="heatCanvasEl" class="heat-canvas"></canvas>
              <div class="map-controls">
                <v-btn-toggle v-model="mapMode" density="compact" mandatory>
                  <v-btn value="heatmap" prepend-icon="mdi-fire" class="mode-btn">Heatmap</v-btn>
                  <v-btn value="routes" prepend-icon="mdi-map-marker-path" class="mode-btn">{{ t('routes') }}</v-btn>
                </v-btn-toggle>
                <div class="map-toggle-group">
                  <span>Grid</span>
                  <div class="segmented-control three" role="group" :aria-label="t('heatmapGrid')">
                    <button
                      v-for="size in heatmapGridOptions"
                      :key="size"
                      type="button"
                      :class="['segment-button', { active: heatmapGrid === size }]"
                      @click="setHeatmapGrid(size)"
                    >
                      <span>{{ size }} m</span>
                    </button>
                  </div>
                </div>
                <div class="map-toggle-group">
                  <span>{{ t('display') }}</span>
                  <div class="segmented-control" role="group" :aria-label="t('heatmapDisplay')">
                    <button
                      type="button"
                      :class="['segment-button', { active: showFrequency }]"
                      @click="setHeatmapWeightMode('frequency')"
                    >
                      <v-icon icon="mdi-brightness-6" size="18" />
                      <span>{{ t('frequency') }}</span>
                    </button>
                    <button
                      type="button"
                      :class="['segment-button', { active: !showFrequency }]"
                      @click="setHeatmapWeightMode('plain')"
                    >
                      <v-icon icon="mdi-map-marker-path" size="18" />
                      <span>{{ t('plainRoute') }}</span>
                    </button>
                  </div>
                </div>
                <div class="map-slider">
                  <span>{{ t('line') }} {{ lineStrength.toFixed(1) }}</span>
                  <v-slider
                    v-model="lineStrength"
                    :min="0.5"
                    :max="2"
                    :step="0.1"
                    hide-details
                    density="compact"
                    color="primary"
                  />
                </div>
                <div class="map-slider">
                  <span>{{ t('glow') }} {{ glowStrength.toFixed(1) }}</span>
                  <v-slider
                    v-model="glowStrength"
                    :min="0"
                    :max="2"
                    :step="0.1"
                    hide-details
                    density="compact"
                    color="primary"
                  />
                </div>
              </div>
              <div v-if="heatmapBusy" class="map-busy">
                <div class="loading-progress"><span /></div>
                <strong>{{ t('drawingHeatmap') }}</strong>
                <span>{{ heatmapStatus }}</span>
              </div>
              <div v-else-if="mapError" class="map-empty map-error">
                <v-icon icon="mdi-alert-circle-outline" />
                <span>{{ mapError }}</span>
                <v-btn size="small" variant="tonal" @click="initMap">{{ t('redraw') }}</v-btn>
              </div>
              <div v-else-if="!roadFeatureCount" class="map-empty">
                <v-icon icon="mdi-map-marker-off-outline" />
                <span>{{ t('noRoutesForFilter') }}</span>
              </div>
              <div v-else class="heatmap-meta">
                {{ roadRouteCount }} {{ t('routesLower') }} ·
                {{ roadHeatmapData.properties?.stretches || 0 }} {{ t('segmentsLower') }} ·
                {{ heatmapLegendLabel }}
              </div>
            </div>
          </div>

          <div v-if="view === 'trips'" class="trips-layout">
            <v-data-table
              :headers="tripHeaders"
              :items="filteredTrips"
              :items-per-page="15"
              density="compact"
              item-value="id"
              hover
              @click:row="selectTrip"
            >
              <template #item.started_at="{ item }">{{ formatDate(item.started_at) }}</template>
              <template #item.distance="{ item }">{{ formatKm(item.distance) }}</template>
              <template #item.unlocked_time="{ item }">{{ formatDuration(item.unlocked_time || item.moving_time) }}</template>
              <template #item.has_dashboard_data="{ item }">
                <v-icon :color="item.has_dashboard_data ? 'primary' : 'grey'" :icon="item.has_dashboard_data ? 'mdi-map-marker-path' : 'mdi-minus'" />
              </template>
            </v-data-table>
            <aside class="trip-detail">
              <template v-if="selectedTrip">
                <h2>{{ selectedTrip.trip?.title || `Trip ${selectedTrip.trip?.id}` }}</h2>
                <div ref="tripMapEl" class="trip-map"></div>
                <dl>
                  <dt>Start</dt><dd>{{ formatDate(selectedTrip.trip?.started_at) }}</dd>
                  <dt>{{ t('distance') }}</dt><dd>{{ formatKm(selectedTrip.trip?.distance) }}</dd>
                  <dt>{{ t('route') }}</dt><dd>{{ selectedTrip.charts ? t('available') : t('notLoaded') }}</dd>
                </dl>
              </template>
            </aside>
          </div>
        </section>
      </v-main>
    </v-layout>
    <div v-if="loading || syncing" class="native-loading">
      <div class="loading-box">
        <div class="loading-progress"><span /></div>
        <div class="native-spinner" aria-hidden="true" />
        <strong>{{ loadingMessage }}</strong>
        <span>{{ loadingHint }}</span>
      </div>
    </div>
  </v-app>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import * as maplibregl from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { api } from './api'

maplibregl.setWorkerUrl(maplibreWorkerUrl)

const authenticated = ref(false)
const drawer = ref(true)
const rail = ref(false)
const view = ref('dashboard')
const email = ref('')
const password = ref('')
const loading = ref(false)
const syncing = ref(false)
const error = ref('')
const overview = ref({})
const me = ref({})
const trips = ref([])
const selectedTrip = ref(null)
const mapEl = ref(null)
const map = ref(null)
const heatCanvasEl = ref(null)
const tripMapEl = ref(null)
const tripMap = ref(null)
const heatmapData = ref({ type: 'FeatureCollection', features: [] })
const roadHeatmapData = ref({ type: 'FeatureCollection', features: [], properties: {} })
const heatmapBusy = ref(false)
const mapError = ref('')
const profileAvatarFailed = ref(false)
const mapReady = ref(false)
const showFrequency = ref(true)
const mapMode = ref('heatmap')
const heatmapGrid = ref(50)
const heatmapGridOptions = [5, 20, 50]
const lineStrength = ref(1)
const glowStrength = ref(1)
const syncDays = ref(400)
const syncFull = ref(false)
const dateFrom = ref('')
const dateTo = ref('')
const selectedYear = ref('')
const selectedMonth = ref('')
const selectedDay = ref('')
const language = ref(localStorage.getItem('cowboy-dashboard-language') || 'de')
const languageOptions = [
  { value: 'de', label: 'Deutsch' },
  { value: 'en', label: 'English' },
]

const messages = {
  de: {
    loginLead: '',
    language: 'Sprache',
    signIn: 'Anmelden',
    credentialNotice: 'Die Zugangsdaten bleiben im Backend und werden nicht im Browser gespeichert.',
    email: 'E-Mail',
    password: 'Passwort',
    passwordPlaceholder: 'Cowboy Passwort',
    loginButton: 'Login',
    dashboard: 'Dashboard',
    heatmap: 'Heatmap',
    tripsNav: 'Fahrten',
    startSync: 'Sync starten',
    syncAllTrips: 'Alle Fahrten synchronisieren',
    reload: 'Neu laden',
    battery: 'Akku',
    range: 'Reichweite',
    signal: 'Signal',
    from: 'Von',
    to: 'Bis',
    reset: 'Reset',
    batteryLevel: 'Akku-Stand',
    batteryInserted: 'Akku im Bike',
    lastSignal: 'Letztes Signal',
    yes: 'ja',
    no: 'nein',
    period: 'Zeitraum',
    syncPeriod: 'Sync-Zeitraum',
    about12Months: 'ca. 12 Monate',
    about3Years: 'ca. 3 Jahre',
    allTrips: 'alle Fahrten',
    fullRelist: 'komplett neu listen',
    relistAllTrips: 'Alle Fahrten neu listen',
    syncMissingTrips: 'Fehlende Fahrten synchronisieren',
    relistAll: 'Alles neu listen',
    trips: 'Fahrten',
    tripsLower: 'Fahrten',
    routes: 'Strecken',
    routesLower: 'Strecken',
    route: 'Route',
    distance: 'Distanz',
    rideTime: 'Fahrzeit',
    average: 'Durchschnitt',
    co2Saved: 'CO2 gespart',
    display: 'Darstellung',
    frequency: 'Häufigkeit',
    plainRoute: 'Nur Strecke',
    drawingHeatmap: 'Heatmap wird gezeichnet',
    redraw: 'Neu zeichnen',
    noRoutesForFilter: 'Keine Routen für diesen Filter.',
    segmentsLower: 'Abschnitte',
    bike: 'Fahrrad',
    name: 'Name',
    model: 'Modell',
    color: 'Farbe',
    statusSubtitle: 'Bike, Akku und Safety',
    batterySoc: 'Akku SoC',
    stolen: 'Gestohlen',
    lastCrash: 'Letzter Crash',
    location: 'Standort',
    accuracy: 'Genauigkeit',
    type: 'Typ',
    received: 'Empfangen',
    autonomiesSubtitle: 'Reichweitenprofile je Fahrmodus; kalibrierte Werte sind am ehesten realistisch.',
    calibrated: 'kalibriert',
    notCalibrated: 'nicht kalibriert',
    noAutonomyData: 'Keine Autonomy-Daten.',
    featuresSubtitle: 'Alles, was die API als Bike-Konfiguration liefert.',
    adjustHeatmap: 'Heatmap anpassen',
    year: 'Jahr',
    allYears: 'alle Jahre',
    month: 'Monat',
    wholeYear: 'ganzes Jahr',
    day: 'Tag',
    wholeMonth: 'ganzer Monat',
    line: 'Linie',
    glow: 'Leuchten',
    available: 'verfügbar',
    notLoaded: 'nicht geladen',
    loginRequired: 'Bitte E-Mail und Passwort eingeben.',
    noSync: 'Noch kein Sync gespeichert',
    lastSync: 'Letzter Sync',
    loadingData: 'Daten werden geladen',
    syncRunning: 'Sync läuft',
    loadingHint: 'Dashboard, Bike-Status und Karte werden aktualisiert.',
    syncHint: 'Cowboy-Fahrten werden aktualisiert, neue Routen werden gespeichert.',
    allTripsScope: 'Alle Fahrten',
    rangeFiltered: 'Statistik und Heatmap sind auf den Datumsbereich gefiltert.',
    dayFiltered: 'Statistik und Heatmap sind auf diesen Tag gefiltert.',
    monthFiltered: 'Statistik und Heatmap sind auf diesen Monat gefiltert.',
    yearFiltered: 'Statistik und Heatmap sind auf dieses Jahr gefiltert.',
    allTripsFiltered: 'Statistik und Heatmap zeigen alle gespeicherten Fahrten.',
    monthsInRange: 'Monate im Datumsbereich',
    daysInRange: 'Tage im Datumsbereich',
    daysIn: 'Tage in',
    monthsIn: 'Monate in',
    kmPerYear: 'Kilometer pro Jahr',
    rangeHint: 'Datumsbereich aktiv. Balken zeigen nur diesen Zeitraum.',
    dayHint: 'Klick auf einen Tag filtert Statistik und Heatmap.',
    monthHint: 'Klick auf einen Monat zoomt in die Tagesansicht.',
    yearHint: 'Klick auf ein Jahr zoomt in die Monatsansicht.',
    filter: 'Filter',
    highlightedFrequency: 'Häufigkeit hervorgehoben',
    onlyRoutes: 'nur Strecken',
    withoutFrequency: 'ohne Häufigkeitsgewichtung',
    max: 'max',
    dateRange: 'Datumsbereich',
    since: 'ab',
    until: 'bis',
    date: 'Datum',
    title: 'Titel',
    duration: 'Dauer',
    mapInitError: 'Karte konnte nicht initialisiert werden.',
    heatmapGrid: 'Heatmap-Grid',
    heatmapDisplay: 'Heatmap-Darstellung',
  },
  en: {
    loginLead: '',
    language: 'Language',
    signIn: 'Sign in',
    credentialNotice: 'Credentials stay in the backend and are not stored in the browser.',
    email: 'Email',
    password: 'Password',
    passwordPlaceholder: 'Cowboy password',
    loginButton: 'Sign in',
    dashboard: 'Dashboard',
    heatmap: 'Heatmap',
    tripsNav: 'Rides',
    startSync: 'Start sync',
    syncAllTrips: 'Sync all rides',
    reload: 'Reload',
    battery: 'Battery',
    range: 'Range',
    signal: 'Signal',
    from: 'From',
    to: 'To',
    reset: 'Reset',
    batteryLevel: 'Battery level',
    batteryInserted: 'Battery in bike',
    lastSignal: 'Last signal',
    yes: 'yes',
    no: 'no',
    period: 'Period',
    syncPeriod: 'Sync period',
    about12Months: 'about 12 months',
    about3Years: 'about 3 years',
    allTrips: 'all rides',
    fullRelist: 'fully relist',
    relistAllTrips: 'Relist all rides',
    syncMissingTrips: 'Sync missing rides',
    relistAll: 'Relist all',
    trips: 'Rides',
    tripsLower: 'rides',
    routes: 'Routes',
    routesLower: 'routes',
    route: 'Route',
    distance: 'Distance',
    rideTime: 'Ride time',
    average: 'Average',
    co2Saved: 'CO2 saved',
    display: 'Display',
    frequency: 'Frequency',
    plainRoute: 'Plain route',
    drawingHeatmap: 'Drawing heatmap',
    redraw: 'Redraw',
    noRoutesForFilter: 'No routes for this filter.',
    segmentsLower: 'segments',
    bike: 'Bike',
    name: 'Name',
    model: 'Model',
    color: 'Color',
    statusSubtitle: 'Bike, battery, and safety',
    batterySoc: 'Battery SoC',
    stolen: 'Stolen',
    lastCrash: 'Last crash',
    location: 'Location',
    accuracy: 'Accuracy',
    type: 'Type',
    received: 'Received',
    autonomiesSubtitle: 'Range profiles per ride mode; calibrated values are likely the most realistic.',
    calibrated: 'calibrated',
    notCalibrated: 'not calibrated',
    noAutonomyData: 'No autonomy data.',
    featuresSubtitle: 'Everything the API exposes as bike configuration.',
    adjustHeatmap: 'Adjust heatmap',
    year: 'Year',
    allYears: 'all years',
    month: 'Month',
    wholeYear: 'whole year',
    day: 'Day',
    wholeMonth: 'whole month',
    line: 'Line',
    glow: 'Glow',
    available: 'available',
    notLoaded: 'not loaded',
    loginRequired: 'Please enter email and password.',
    noSync: 'No sync stored yet',
    lastSync: 'Last sync',
    loadingData: 'Loading data',
    syncRunning: 'Sync running',
    loadingHint: 'Dashboard, bike status, and map are being updated.',
    syncHint: 'Cowboy rides are being updated and new routes are being stored.',
    allTripsScope: 'All rides',
    rangeFiltered: 'Stats and heatmap are filtered to the date range.',
    dayFiltered: 'Stats and heatmap are filtered to this day.',
    monthFiltered: 'Stats and heatmap are filtered to this month.',
    yearFiltered: 'Stats and heatmap are filtered to this year.',
    allTripsFiltered: 'Stats and heatmap show all stored rides.',
    monthsInRange: 'Months in date range',
    daysInRange: 'Days in date range',
    daysIn: 'Days in',
    monthsIn: 'Months in',
    kmPerYear: 'Kilometers per year',
    rangeHint: 'Date range active. Bars show only this period.',
    dayHint: 'Click a day to filter stats and heatmap.',
    monthHint: 'Click a month to zoom into daily view.',
    yearHint: 'Click a year to zoom into monthly view.',
    filter: 'Filter',
    highlightedFrequency: 'frequency highlighted',
    onlyRoutes: 'routes only',
    withoutFrequency: 'without frequency weighting',
    max: 'max',
    dateRange: 'Date range',
    since: 'from',
    until: 'until',
    date: 'Date',
    title: 'Title',
    duration: 'Duration',
    mapInitError: 'Map could not be initialized.',
    heatmapGrid: 'Heatmap grid',
    heatmapDisplay: 'Heatmap display',
  },
}

const t = (key) => messages[language.value]?.[key] || messages.de[key] || key
const locale = computed(() => language.value === 'en' ? 'en-US' : 'de-DE')

const navItems = computed(() => [
  { value: 'dashboard', title: t('dashboard'), icon: 'mdi-view-dashboard-outline' },
  { value: 'heatmap', title: t('heatmap'), icon: 'mdi-map' },
  { value: 'trips', title: t('tripsNav'), icon: 'mdi-format-list-bulleted' },
])

const currentTitle = computed(() => navItems.value.find((item) => item.value === view.value)?.title || t('dashboard'))
const subtitle = computed(() => {
  const sync = overview.value.sync || {}
  return sync.finished_at ? `${t('lastSync')}: ${formatDate(sync.finished_at)}` : t('noSync')
})

const loadingMessage = computed(() => syncing.value ? t('syncRunning') : t('loadingData'))
const loadingHint = computed(() => {
  if (syncing.value) return t('syncHint')
  return t('loadingHint')
})

const profileName = computed(() => {
  const parts = [me.value.first_name, me.value.last_name].filter(Boolean).join(' ').trim()
  return me.value.nickname || parts || me.value.email || me.value.uid || 'Cowboy'
})
const profileAvatarUrl = computed(() => {
  return findAvatarUrl([me.value.avatar_url, me.value.avatar, me.value.avatars, me.value.profile_picture, me.value.picture])
})
const showProfileAvatar = computed(() => Boolean(profileAvatarUrl.value && !profileAvatarFailed.value))
const profileInitials = computed(() => {
  const text = profileName.value || 'Cowboy'
  const initials = text
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
  return initials || 'C'
})

function findAvatarUrl(value) {
  const queue = Array.isArray(value) ? [...value] : [value]
  const seen = new Set()
  while (queue.length) {
    const item = queue.shift()
    if (!item) continue
    if (typeof item === 'string' && /^(https?:|data:image\/)/i.test(item)) return item
    if (typeof item !== 'object' || seen.has(item)) continue
    seen.add(item)
    for (const key of ['url', 'avatar_url', 'image_url', 'src', 'large', 'medium', 'small', 'original']) {
      if (item[key]) queue.unshift(item[key])
    }
    for (const nested of Object.values(item)) {
      if (nested && typeof nested === 'object') queue.push(nested)
    }
  }
  return ''
}
const bike = computed(() => me.value.bike || {})
const bikeName = computed(() => bike.value.nickname || bike.value.serial_number || 'Cowboy')
const bikeModel = computed(() => bike.value.model?.name || bike.value.model?.description || 'Bike')
const bikeColor = computed(() => bike.value.sku?.color || bike.value.color || '-')
const bikeAutonomies = computed(() => Array.isArray(bike.value.autonomies) ? bike.value.autonomies : [])
const bikeFeatures = computed(() => objectEntries(bike.value.available_features))
const bikeSettings = computed(() => objectEntries(bike.value.settings))
const batteryPercent = computed(() => Number(bike.value.battery_state_of_charge ?? 0))
const batteryLabel = computed(() => bike.value.battery_state_of_charge == null ? '-' : `${Math.round(batteryPercent.value)}%`)
const rangeLabel = computed(() => formatNullableKm(bike.value.autonomy ?? bike.value.estimated_range ?? bike.value.range))
const batteryColor = computed(() => {
  if (batteryPercent.value <= 20) return 'error'
  if (batteryPercent.value <= 45) return 'warning'
  return 'primary'
})

const tripHeaders = computed(() => [
  { title: t('date'), key: 'started_at', width: '180px' },
  { title: t('title'), key: 'title' },
  { title: t('distance'), key: 'distance', width: '120px' },
  { title: t('duration'), key: 'unlocked_time', width: '120px' },
  { title: t('route'), key: 'has_dashboard_data', width: '92px', align: 'center' },
])

const selectedStats = computed(() => aggregateTrips(filteredTrips.value))
const hasDateRange = computed(() => Boolean(dateFrom.value || dateTo.value))
const scopeTitle = computed(() => {
  if (hasDateRange.value) return rangeTitle.value
  if (selectedDay.value) return formatDayTitle(selectedDay.value)
  if (selectedMonth.value) return formatMonthTitle(selectedMonth.value)
  if (selectedYear.value) return selectedYear.value
  return t('allTripsScope')
})
const scopeSubtitle = computed(() => {
  if (hasDateRange.value) return t('rangeFiltered')
  if (selectedDay.value) return t('dayFiltered')
  if (selectedMonth.value) return t('monthFiltered')
  if (selectedYear.value) return t('yearFiltered')
  return t('allTripsFiltered')
})
const metricScopeLabel = computed(() => scopeTitle.value)
const rangeTitle = computed(() => {
  if (dateFrom.value && dateTo.value) return `${formatPlainDate(dateFrom.value)} - ${formatPlainDate(dateTo.value)}`
  if (dateFrom.value) return `${t('since')} ${formatPlainDate(dateFrom.value)}`
  if (dateTo.value) return `${t('until')} ${formatPlainDate(dateTo.value)}`
  return t('dateRange')
})
const chartLevel = computed(() => {
  if (hasDateRange.value) return rangeBucketLevel.value
  if (selectedMonth.value) return 'day'
  if (selectedYear.value) return 'month'
  return 'year'
})
const rangeBucketLevel = computed(() => rangeSpanDays.value > 95 ? 'month' : 'day')
const chartTitle = computed(() => {
  if (hasDateRange.value) return rangeBucketLevel.value === 'month' ? t('monthsInRange') : t('daysInRange')
  if (chartLevel.value === 'day') return `${t('daysIn')} ${formatMonthTitle(selectedMonth.value)}`
  if (chartLevel.value === 'month') return `${t('monthsIn')} ${selectedYear.value}`
  return t('kmPerYear')
})
const chartHint = computed(() => {
  if (hasDateRange.value) return t('rangeHint')
  if (chartLevel.value === 'day') return t('dayHint')
  if (chartLevel.value === 'month') return t('monthHint')
  return t('yearHint')
})
const chartBuckets = computed(() => {
  if (hasDateRange.value) return rangeBuckets.value
  if (chartLevel.value === 'day') return dailyBuckets.value
  if (chartLevel.value === 'month') return monthlyBuckets.value
  return yearlyBuckets.value
})
const rangeBuckets = computed(() => {
  const buckets = new Map()
  const keyLength = rangeBucketLevel.value === 'month' ? 7 : 10
  for (const trip of trips.value) {
    if (!matchesDateRange(trip.started_at)) continue
    addTripToBucket(buckets, trip.started_at.slice(0, keyLength), trip)
  }
  return [...buckets.values()].sort((a, b) => a.key.localeCompare(b.key))
})
const rangeSpanDays = computed(() => {
  if (!dateFrom.value || !dateTo.value) return 0
  const from = new Date(`${dateFrom.value}T00:00:00`)
  const to = new Date(`${dateTo.value}T00:00:00`)
  return Math.max(0, Math.round((to - from) / 86400000) + 1)
})
const visibleChartBuckets = computed(() => chartBuckets.value)
const yearlyBuckets = computed(() => {
  const byYear = new Map()
  for (const trip of trips.value) {
    if (!trip.started_at) continue
    const year = trip.started_at.slice(0, 4)
    addTripToBucket(byYear, year, trip)
  }
  return [...byYear.values()].sort((a, b) => a.key.localeCompare(b.key))
})
const monthlyBuckets = computed(() => {
  const byMonth = new Map()
  for (const trip of trips.value) {
    if (!trip.started_at || !trip.started_at.startsWith(selectedYear.value)) continue
    const month = trip.started_at.slice(0, 7)
    addTripToBucket(byMonth, month, trip)
  }
  return [...byMonth.values()].sort((a, b) => a.key.localeCompare(b.key))
})
const dailyBuckets = computed(() => {
  const byDay = new Map()
  for (const trip of trips.value) {
    if (!trip.started_at || !trip.started_at.startsWith(selectedMonth.value)) continue
    const day = trip.started_at.slice(0, 10)
    addTripToBucket(byDay, day, trip)
  }
  return [...byDay.values()].sort((a, b) => a.key.localeCompare(b.key))
})

const chartSeries = computed(() => {
  const entries = visibleChartBuckets.value
  return [{ name: 'km', data: entries.map((entry) => Number(entry.distanceKm.toFixed(1))) }]
})

const chartOptions = computed(() => {
  const buckets = visibleChartBuckets.value
  return {
    chart: {
      toolbar: { show: false },
      fontFamily: 'Inter, system-ui, sans-serif',
    },
    colors: ['#b33a32'],
    grid: { borderColor: '#e3e1da' },
    plotOptions: { bar: { borderRadius: 3, columnWidth: '58%' } },
    dataLabels: { enabled: false },
    states: {
      hover: { filter: { type: 'lighten', value: 0.04 } },
      active: { filter: { type: 'darken', value: 0.08 } },
    },
    tooltip: {
      shared: false,
      intersect: true,
      y: { formatter: (value) => `${Number(value || 0).toLocaleString(locale.value, { maximumFractionDigits: 1 })} km` },
    },
    xaxis: {
      categories: buckets.map((bucket) => bucket.label),
      axisBorder: { color: 'rgba(229, 236, 231, 0.45)' },
      axisTicks: { color: 'rgba(229, 236, 231, 0.45)' },
      labels: {
        rotate: -30,
        style: { colors: '#dce8e1' },
      },
    },
    yaxis: {
      labels: {
        formatter: (value) => `${Math.round(value)} km`,
        style: { colors: '#dce8e1' },
      },
    },
  }
})

const filteredTrips = computed(() => {
  return trips.value.filter((trip) => matchesSelectedDate(trip.started_at))
})

const filteredGeojson = computed(() => {
  return {
    type: 'FeatureCollection',
    features: (heatmapData.value.features || []).filter((feature) =>
      matchesSelectedDate(feature.properties?.started_at),
    ),
    properties: heatmapData.value.properties || {},
  }
})

const filteredFeatureCount = computed(() => filteredGeojson.value.features.length)
const roadFeatureCount = computed(() => roadHeatmapData.value.features?.length || 0)
const roadRouteCount = computed(() => roadHeatmapData.value.properties?.routes ?? roadHeatmapData.value.properties?.trips ?? 0)
const heatmapStatus = computed(() => {
  const props = roadHeatmapData.value.properties || {}
  const prefix = selectedDatePrefix()
  const scope = prefix ? `${t('filter')} ${prefix}` : t('allTrips')
  const mode = showFrequency.value && mapMode.value === 'heatmap'
    ? t('highlightedFrequency')
    : t('onlyRoutes')
  return `${roadRouteCount.value} ${t('routesLower')}, ${props.stretches || 0} ${t('segmentsLower')}, Grid ${props.grid_m || heatmapGrid.value} m, ${scope}, ${mode}`
})

const heatmapLegendLabel = computed(() => {
  if (showFrequency.value && mapMode.value === 'heatmap') {
    return `${t('max')} ${roadHeatmapData.value.properties?.max_count || 0}x`
  }
  return t('withoutFrequency')
})

const daysInSelectedMonth = computed(() => {
  if (!selectedMonth.value) return []
  const dates = new Set()
  for (const trip of trips.value) {
    const started = trip.started_at || ''
    if (started.startsWith(selectedMonth.value)) {
      dates.add(started.slice(0, 10))
    }
  }
  return [...dates].sort().map((value) => ({
    value,
    label: new Intl.DateTimeFormat(locale.value, {
      weekday: 'short',
      day: '2-digit',
      month: '2-digit',
    }).format(new Date(value)),
  }))
})

const availableYears = computed(() => yearlyBuckets.value.map((bucket) => bucket.key))
const monthsInSelectedYear = computed(() => {
  if (!selectedYear.value) return []
  return monthlyBuckets.value.map((bucket) => ({
    value: bucket.key,
    label: formatMonthOnly(bucket.key),
  }))
})

onMounted(async () => {
  await checkSession()
})

watch(language, (value) => {
  localStorage.setItem('cowboy-dashboard-language', value)
})

watch(profileAvatarUrl, () => {
  profileAvatarFailed.value = false
})

watch(view, async (value) => {
  if (value === 'dashboard' || value === 'heatmap') {
    await nextTick()
    await refreshRoadHeatmap()
    await nextTick()
    initMap()
  } else if (map.value) {
    map.value.remove()
    map.value = null
    mapReady.value = false
  }
})

watch([selectedYear, selectedMonth, selectedDay, dateFrom, dateTo, heatmapGrid], async () => {
  if (!selectedYear.value && (selectedMonth.value || selectedDay.value)) {
    selectedMonth.value = ''
    selectedDay.value = ''
    return
  }
  if (selectedMonth.value && selectedYear.value && !selectedMonth.value.startsWith(selectedYear.value)) {
    selectedMonth.value = ''
    selectedDay.value = ''
    return
  }
  if (selectedDay.value && selectedMonth.value && !selectedDay.value.startsWith(selectedMonth.value)) {
    selectedDay.value = ''
    return
  }
  await refreshRoadHeatmap()
})

watch([heatmapData, roadHeatmapData, mapMode, showFrequency, lineStrength, glowStrength], () => {
  renderHeatmap()
})

async function checkSession() {
  loading.value = true
  try {
    const session = await api.session()
    authenticated.value = session.authenticated
    if (authenticated.value) {
      await refreshAll()
      await nextTick()
      initMap()
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function login() {
  error.value = ''
  if (!email.value || !password.value) {
    error.value = t('loginRequired')
    return
  }
  loading.value = true
  try {
    await api.login(email.value, password.value)
    password.value = ''
    authenticated.value = true
    view.value = 'dashboard'
    await refreshAll()
    await nextTick()
    initMap()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function logout() {
  await api.logout()
  authenticated.value = false
  selectedTrip.value = null
}

async function refreshAll() {
  loading.value = true
  try {
    const meData = await api.me()
    let bikeData = meData.bike || {}
    if (bikeData.id) {
      try {
        bikeData = await api.bike(bikeData.id)
      } catch {
        bikeData = meData.bike || {}
      }
    }
    const [overviewData, tripData, geojson, roads] = await Promise.all([
      api.overview(),
      api.trips(),
      api.heatmap(),
      api.roadHeatmap(roadHeatmapParams()),
    ])
    me.value = { ...meData, bike: bikeData }
    overview.value = overviewData
    trips.value = tripData
    heatmapData.value = geojson
    roadHeatmapData.value = roads
    renderHeatmap()
  } finally {
    loading.value = false
  }
}

async function refreshRoadHeatmap() {
  if (!authenticated.value) return
  heatmapBusy.value = true
  try {
    roadHeatmapData.value = await api.roadHeatmap(roadHeatmapParams())
    await nextTick()
    renderHeatmap()
  } finally {
    heatmapBusy.value = false
  }
}

async function runSync(full) {
  error.value = ''
  syncing.value = true
  try {
    await api.syncTrips({ days: syncDays.value, overlap_days: 7, full, workers: 4, chart_delay: 0 })
    await refreshAll()
  } catch (err) {
    error.value = err.message
  } finally {
    syncing.value = false
  }
}

async function syncMissingTrips() {
  syncFull.value = false
  await runSync(false)
}

async function syncAllTrips() {
  syncDays.value = 5000
  syncFull.value = true
  await runSync(true)
}

function clearMapFilters() {
  selectedYear.value = ''
  selectedMonth.value = ''
  selectedDay.value = ''
}

function clearDateRange() {
  dateFrom.value = ''
  dateTo.value = ''
}

function clearDrilldownForRange() {
  if (!hasDateRange.value) return
  selectedYear.value = ''
  selectedMonth.value = ''
  selectedDay.value = ''
}

function resetFilters() {
  clearMapFilters()
  clearDateRange()
}

function setHeatmapWeightMode(value) {
  if (!value) return
  showFrequency.value = value === 'frequency'
  renderHeatmap()
}

function setHeatmapGrid(size) {
  if (!heatmapGridOptions.includes(size)) return
  heatmapGrid.value = size
}

function handleChartSelection(_event, _chartContext, config) {
  if (hasDateRange.value) return
  const index = Number(config?.dataPointIndex)
  if (index < 0 || Number.isNaN(index)) return
  const bucket = visibleChartBuckets.value[index]
  if (!bucket) return
  if (chartLevel.value === 'year') {
    selectedYear.value = bucket.key
    selectedMonth.value = ''
    selectedDay.value = ''
  } else if (chartLevel.value === 'month') {
    selectedMonth.value = bucket.key
    selectedDay.value = ''
  } else {
    selectedDay.value = bucket.key
  }
}

async function selectTrip(_event, row) {
  const item = row.item?.raw || row.item
  selectedTrip.value = await api.trip(item.id)
  await nextTick()
  renderTripMap()
}

function initMap() {
  if (!mapEl.value) return
  mapError.value = ''
  if (map.value) {
    map.value.resize()
    renderHeatmap()
    window.setTimeout(() => {
      map.value?.resize()
      renderHeatmap()
    }, 80)
    return
  }
  try {
    mapReady.value = false
    map.value = new maplibregl.Map({
      container: mapEl.value,
      style: mapStyle(),
      center: [13.7373, 51.0504],
      zoom: 11,
    })
    map.value.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.value.on('move', drawCanvasHeatmap)
    map.value.on('zoom', drawCanvasHeatmap)
    map.value.on('resize', drawCanvasHeatmap)
    const onReady = () => {
      mapReady.value = true
      map.value?.resize()
      renderHeatmap()
      window.setTimeout(() => {
        map.value?.resize()
        renderHeatmap()
      }, 150)
    }
    map.value.on('style.load', onReady)
    map.value.on('load', onReady)
  } catch (err) {
    mapError.value = err.message || t('mapInitError')
  }
}

function renderHeatmap() {
  if (!map.value || !mapReady.value) return
  mapError.value = ''
  map.value.resize()
  const heatCoords = featureCoordinates(roadHeatmapData.value)
  const routeCoords = featureCoordinates(filteredGeojson.value)
  const coords = mapMode.value === 'heatmap' && heatCoords.length ? heatCoords : routeCoords
  const focusCoords = shouldFocusLatestRide() ? latestRideCoordinates() : coords
  if (focusCoords.length) {
    const bounds = focusCoords.reduce((box, coord) => box.extend(coord), new maplibregl.LngLatBounds(focusCoords[0], focusCoords[0]))
    map.value.fitBounds(bounds, { padding: 60, maxZoom: 17, duration: 0 })
  }
  window.requestAnimationFrame(drawCanvasHeatmap)
}

function shouldFocusLatestRide() {
  return !hasDateRange.value && !selectedYear.value && !selectedMonth.value && !selectedDay.value
}

function latestRideCoordinates() {
  const features = [...(heatmapData.value.features || [])]
    .filter((feature) => feature.properties?.started_at)
    .sort((a, b) => String(b.properties.started_at).localeCompare(String(a.properties.started_at)))
  for (const feature of features) {
    const coords = featureCoordinates({ features: [feature] })
    if (coords.length >= 2) return coords
  }
  return featureCoordinates(heatmapData.value)
}

function drawCanvasHeatmap() {
  if (!map.value || !heatCanvasEl.value || !mapEl.value) return
  const canvas = heatCanvasEl.value
  const bounds = mapEl.value.getBoundingClientRect()
  const mapBounds = map.value.getBounds()
  const dpr = window.devicePixelRatio || 1
  const width = Math.max(1, Math.round(bounds.width))
  const height = Math.max(1, Math.round(bounds.height))
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr)
    canvas.height = Math.round(height * dpr)
    canvas.style.width = `${width}px`
    canvas.style.height = `${height}px`
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)
  const collection = mapMode.value === 'heatmap' ? roadHeatmapData.value : filteredGeojson.value
  const features = [...(collection.features || [])].sort((a, b) =>
    (a.properties?.weight || 0) - (b.properties?.weight || 0),
  )
  const linesToDraw = []
  const maxLines = mapMode.value === 'heatmap' ? 7000 : 260
  for (let featureIdx = features.length - 1; featureIdx >= 0 && linesToDraw.length < maxLines; featureIdx -= 1) {
    const feature = features[featureIdx]
    const weight = Number(feature.properties?.weight ?? 0.35)
    const lines = feature.geometry?.type === 'MultiLineString'
      ? feature.geometry.coordinates
      : [feature.geometry?.coordinates || []]
    for (const line of lines) {
      if (!line || line.length < 2 || !lineIntersectsBounds(line, mapBounds)) continue
      linesToDraw.push({ line, weight })
      if (linesToDraw.length >= maxLines) break
    }
  }
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  const weightedHeatmap = showFrequency.value && mapMode.value === 'heatmap'
  ctx.globalCompositeOperation = weightedHeatmap ? 'lighter' : 'source-over'
  for (let idx = linesToDraw.length - 1; idx >= 0; idx -= 1) {
    const { line, weight } = linesToDraw[idx]
    const color = heatColor(weight)
    ctx.strokeStyle = color
    const width = weightedHeatmap ? 2.6 + weight * 12 : 3.4
    const blur = weightedHeatmap ? 5 + weight * 8 : 0
    ctx.lineWidth = width * lineStrength.value
    ctx.shadowBlur = blur * glowStrength.value
    ctx.shadowColor = color
    ctx.beginPath()
    for (let pointIdx = 0; pointIdx < line.length; pointIdx += 1) {
      const point = map.value.project(line[pointIdx])
      if (pointIdx === 0) ctx.moveTo(point.x, point.y)
      else ctx.lineTo(point.x, point.y)
    }
    ctx.stroke()
  }
  ctx.globalCompositeOperation = 'source-over'
  ctx.shadowBlur = 0
}

function lineIntersectsBounds(line, bounds) {
  return line.some((coord) => bounds.contains(coord))
}

function heatColor(weight) {
  if (mapMode.value === 'routes') return 'rgb(255, 244, 220)'
  if (!showFrequency.value) return 'rgb(255, 91, 56)'
  if (weight >= 0.78) return 'rgba(255, 243, 220, 0.98)'
  if (weight >= 0.48) return 'rgba(255, 143, 39, 0.9)'
  if (weight >= 0.22) return 'rgba(220, 58, 27, 0.78)'
  return 'rgba(176, 35, 24, 0.58)'
}

function featureCoordinates(collection) {
  return (collection.features || []).flatMap((feature) => {
    const coords = feature.geometry?.coordinates || []
    if (feature.geometry?.type === 'LineString') return coords
    if (feature.geometry?.type === 'MultiLineString') return coords.flat()
    return []
  })
}

function selectedDatePrefix() {
  if (hasDateRange.value) return ''
  return selectedDay.value || selectedMonth.value || selectedYear.value || ''
}

function roadHeatmapParams() {
  return {
    grid: heatmapGrid.value,
    datePrefix: selectedDatePrefix(),
    dateFrom: dateFrom.value,
    dateTo: dateTo.value,
  }
}

function addTripToBucket(map, key, trip) {
  if (!map.has(key)) {
    map.set(key, {
      key,
      label: formatBucketLabel(key),
      trips: [],
      distanceKm: 0,
      durationS: 0,
    })
  }
  const bucket = map.get(key)
  bucket.trips.push(trip)
  bucket.distanceKm += Number(trip.distance || 0)
  bucket.durationS += Number(trip.unlocked_time || trip.moving_time || trip.duration || 0)
}

function formatBucketLabel(key) {
  if (key.length === 4) return key
  if (key.length === 7) return formatMonthOnly(key)
  return formatDayShort(key)
}

function aggregateTrips(items) {
  const totals = items.reduce((state, trip) => {
    const duration = Number(trip.unlocked_time || trip.moving_time || trip.duration || 0)
    const distance = Number(trip.distance || 0)
    state.tripCount += 1
    state.routeCount += trip.has_dashboard_data ? 1 : 0
    state.distanceKm += distance
    state.durationS += duration
    state.movingTimeS += Number(trip.moving_time || duration || 0)
    state.userPowerSum += Number(trip.average_user_power || 0)
    state.motorPowerSum += Number(trip.average_motor_power || 0)
    state.userPowerCount += trip.average_user_power == null ? 0 : 1
    state.motorPowerCount += trip.average_motor_power == null ? 0 : 1
    state.co2Saved += Number(trip.co2_saved || 0)
    state.caloriesBurned += Number(trip.calories_burned || 0)
    return state
  }, {
    tripCount: 0,
    routeCount: 0,
    distanceKm: 0,
    durationS: 0,
    movingTimeS: 0,
    userPowerSum: 0,
    userPowerCount: 0,
    motorPowerSum: 0,
    motorPowerCount: 0,
    co2Saved: 0,
    caloriesBurned: 0,
  })

  return {
    ...totals,
    distanceKm: Number(totals.distanceKm.toFixed(2)),
    averageSpeedKmh: totals.movingTimeS ? totals.distanceKm / (totals.movingTimeS / 3600) : 0,
    averageUserPower: totals.userPowerCount ? totals.userPowerSum / totals.userPowerCount : null,
    averageMotorPower: totals.motorPowerCount ? totals.motorPowerSum / totals.motorPowerCount : null,
  }
}

function objectEntries(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.entries(value).map(([key, item]) => ({
    key,
    label: key.replaceAll('_', ' '),
    value: typeof item === 'boolean' ? yesNo(item) : String(item),
  }))
}

function renderTripMap() {
  if (!tripMapEl.value || !selectedTrip.value?.charts) return
  const coords = (selectedTrip.value.charts.positions || [])
    .filter((point) => point && point.length === 2 && point[0] !== null && point[1] !== null)
    .map((point) => [point[1], point[0]])
  if (coords.length < 2) return
  const data = {
    type: 'FeatureCollection',
    features: [{
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: coords },
      properties: {},
    }],
  }
  if (!tripMap.value) {
    tripMap.value = new maplibregl.Map({
      container: tripMapEl.value,
      style: mapStyle(),
      center: coords[0],
      zoom: 13,
      attributionControl: false,
    })
    tripMap.value.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    tripMap.value.on('load', () => drawTripRoute(data, coords))
  } else if (tripMap.value.isStyleLoaded()) {
    drawTripRoute(data, coords)
  }
}

function drawTripRoute(data, coords) {
  const source = tripMap.value.getSource('selected-trip')
  if (source) {
    source.setData(data)
  } else {
    tripMap.value.addSource('selected-trip', { type: 'geojson', data })
    tripMap.value.addLayer({
      id: 'selected-trip-glow',
      type: 'line',
      source: 'selected-trip',
      paint: {
        'line-color': '#b33a32',
        'line-opacity': 0.32,
        'line-width': 8,
      },
    })
    tripMap.value.addLayer({
      id: 'selected-trip-core',
      type: 'line',
      source: 'selected-trip',
      paint: {
        'line-color': '#2f6f5e',
        'line-opacity': 0.95,
        'line-width': 3,
      },
    })
  }
  const bounds = coords.reduce((box, coord) => box.extend(coord), new maplibregl.LngLatBounds(coords[0], coords[0]))
  tripMap.value.fitBounds(bounds, { padding: 24, maxZoom: 17, duration: 0 })
}

function mapStyle() {
  return {
    version: 8,
    sources: {
      osm: {
        type: 'raster',
        tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
        tileSize: 256,
        attribution: 'OpenStreetMap contributors',
      },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#101713' } },
      {
        id: 'osm',
        type: 'raster',
        source: 'osm',
        paint: {
          'raster-opacity': 0.38,
          'raster-saturation': -0.7,
          'raster-brightness-min': 0.08,
          'raster-brightness-max': 0.7,
        },
      },
    ],
  }
}

function matchesSelectedDate(value) {
  if (hasDateRange.value) return matchesDateRange(value)
  if (!value) return !selectedYear.value && !selectedMonth.value && !selectedDay.value
  if (selectedDay.value) return value.startsWith(selectedDay.value)
  if (selectedMonth.value) return value.startsWith(selectedMonth.value)
  if (selectedYear.value) return value.startsWith(selectedYear.value)
  return true
}

function matchesDateRange(value) {
  if (!value) return !hasDateRange.value
  const day = value.slice(0, 10)
  if (dateFrom.value && day < dateFrom.value) return false
  if (dateTo.value && day > dateTo.value) return false
  return true
}

function formatKm(value) {
  return `${Number(value || 0).toLocaleString(locale.value, { maximumFractionDigits: 1 })} km`
}

function formatNullableKm(value) {
  if (value === null || value === undefined || value === '') return '-'
  return formatKm(value)
}

function formatDuration(seconds) {
  const total = Number(seconds || 0)
  const hours = Math.floor(total / 3600)
  const minutes = Math.round((total % 3600) / 60)
  return hours ? `${hours} h ${minutes} min` : `${minutes} min`
}

function formatSpeed(value) {
  return `${Number(value || 0).toLocaleString(locale.value, { maximumFractionDigits: 1 })} km/h`
}

function formatWatts(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Math.round(Number(value)).toLocaleString(locale.value)} W`
}

function formatPercent(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toLocaleString(locale.value, { maximumFractionDigits: 1 })}%`
}

function formatGrams(value) {
  const grams = Number(value || 0)
  if (!grams) return '-'
  if (grams >= 1000) return `${(grams / 1000).toLocaleString(locale.value, { maximumFractionDigits: 1 })} kg`
  return `${Math.round(grams).toLocaleString(locale.value)} g`
}

function formatMeters(value) {
  if (value === null || value === undefined || value === '') return '-'
  return `${Number(value).toLocaleString(locale.value, { maximumFractionDigits: 1 })} m`
}

function formatCoordinate(value) {
  if (value === null || value === undefined || value === '') return '-'
  return Number(value).toLocaleString(locale.value, { maximumFractionDigits: 5 })
}

function yesNo(value) {
  if (value === null || value === undefined) return '-'
  return value ? t('yes') : t('no')
}

function formatRideMode(value) {
  if (!value) return '-'
  return String(value).replaceAll('_', ' ')
}

function formatMonthTitle(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${value}-01T12:00:00`))
}

function formatMonthOnly(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    month: 'long',
  }).format(new Date(`${value}-01T12:00:00`))
}

function formatDayTitle(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function formatDayShort(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    day: '2-digit',
    month: '2-digit',
  }).format(new Date(`${value}T12:00:00`))
}

function formatPlainDate(value) {
  if (!value) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(`${value}T12:00:00`))
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '-'
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}
</script>
