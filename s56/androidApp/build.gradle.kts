plugins {
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.compose.compiler)
    alias(libs.plugins.android.application)
}

android {
    namespace = "csvui.android"
    compileSdk = 34

    defaultConfig {
        applicationId = "csvui.android"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    buildFeatures {
        compose = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons)
    implementation(libs.compose.foundation)
    implementation(libs.activity.compose)
    implementation(libs.compose.ui.tooling)
}

kotlin {
    sourceSets {
        main {
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/model")
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/csv")
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/actions")
        }
    }
}
