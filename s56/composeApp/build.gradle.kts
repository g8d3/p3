import org.jetbrains.compose.desktop.application.dsl.TargetFormat

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.compose)
    alias(libs.plugins.compose.compiler)
}

dependencies {
    implementation(compose.desktop.currentOs)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)
    testImplementation("org.jetbrains.kotlin:kotlin-test")
}

tasks.named<Test>("test") {
    useJUnitPlatform()
}

compose.desktop {
    application {
        mainClass = "csvui.MainKt"
        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            packageName = "CsvTabulator"
            packageVersion = "1.0.0"
        }
    }
}
