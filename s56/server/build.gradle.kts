plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
    application
}

application {
    mainClass = "webserver.MainKt"
}

dependencies {
    implementation(libs.ktor.server.core)
    implementation(libs.ktor.server.netty)
    implementation(libs.ktor.server.content.negotiation)
    implementation(libs.ktor.serialization.kotlinx.json)
    implementation(libs.ktor.server.status.pages)
    implementation(libs.kotlinx.serialization.json)
}

kotlin {
    jvmToolchain(21)
    sourceSets {
        main {
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/model")
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/csv")
            kotlin.srcDir("../composeApp/src/main/kotlin/csvui/actions")
        }
    }
}

tasks.register<Jar>("fatJar") {
    dependsOn(configurations.runtimeClasspath)
    archiveBaseName.set("csv-tabulator")
    archiveClassifier.set("")
    archiveVersion.set("")
    manifest { attributes["Main-Class"] = "webserver.MainKt" }
    from(sourceSets.main.get().output)
    from(configurations.runtimeClasspath.get().map { if (it.isDirectory) it else zipTree(it) }) {
        exclude("META-INF/*.RSA", "META-INF/*.SF", "META-INF/*.DSA")
    }
    duplicatesStrategy = DuplicatesStrategy.EXCLUDE
}
