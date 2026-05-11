package webserver

import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import io.ktor.server.application.*
import io.ktor.server.engine.*
import io.ktor.server.netty.*
import io.ktor.server.plugins.contentnegotiation.*
import io.ktor.server.plugins.statuspages.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
import kotlinx.serialization.json.Json
import java.io.File

val json = Json {
    prettyPrint = true
    ignoreUnknownKeys = true
}

fun main(args: Array<String>) {
    // Primer argumento = directorio de datos (default: directorio actual)
    val dataDir = if (args.isNotEmpty()) File(args[0]) else File(".")
    if (!dataDir.exists()) {
        println("[csv-tabulator] Error: el directorio '${dataDir.absolutePath}' no existe")
        kotlin.system.exitProcess(1)
    }
    if (!dataDir.isDirectory) {
        println("[csv-tabulator] Error: '${dataDir.absolutePath}' no es un directorio")
        kotlin.system.exitProcess(1)
    }

    println("[csv-tabulator] Directorio de datos: ${dataDir.absolutePath}")
    println("[csv-tabulator] Servidor iniciado en: http://localhost:8080")

    val appState = AppState(dataDir)

    embeddedServer(Netty, port = 8080, host = "0.0.0.0") {
        install(ContentNegotiation) {
            json(json)
        }

        install(StatusPages) {
            exception<Throwable> { call, cause ->
                call.respondText(
                    """{"error":"${cause.message?.replace("\"", "\\\"") ?: "Unknown"}"}""",
                    ContentType.Application.Json,
                    HttpStatusCode.InternalServerError
                )
            }
        }

        routing {
            route("/api") {
                get("/data") { appState.handleGetData(call) }
                get("/info") { appState.handleGetInfo(call) }
                post("/cell") { appState.handleUpdateCell(call) }
                post("/row") { appState.handleRowOp(call) }
                post("/column") { appState.handleColumnOp(call) }
                post("/file") { appState.handleFileOp(call) }
                post("/save") { appState.handleSave(call) }
                post("/action/execute") { appState.handleExecuteAction(call) }
                get("/files") { appState.handleListFiles(call) }
                get("/actions") { appState.handleListActions(call) }
                post("/actions") { appState.handleCreateAction(call) }
                put("/actions/{id}") { appState.handleUpdateAction(call) }
                delete("/actions/{id}") { appState.handleDeleteAction(call) }
            }

            get("/{path...}") {
                val path = call.parameters["path"] ?: ""
                val resourcePath = if (path.isBlank() || path == "/") "web/index.html" else "web/$path"

                val resource = this::class.java.classLoader.getResource(resourcePath)
                if (resource != null) {
                    val content = resource.readBytes()
                    val contentType = when {
                        resourcePath.endsWith(".html") -> ContentType.Text.Html
                        resourcePath.endsWith(".css") -> ContentType.Text.CSS
                        resourcePath.endsWith(".js") -> ContentType.Application.JavaScript
                        resourcePath.endsWith(".json") -> ContentType.Application.Json
                        resourcePath.endsWith(".png") -> ContentType.Image.PNG
                        resourcePath.endsWith(".svg") -> ContentType.Image.SVG
                        resourcePath.endsWith(".ico") -> ContentType.Image.XIcon
                        else -> ContentType.Application.OctetStream
                    }
                    call.respondBytes(content, contentType)
                } else {
                    val indexResource = this::class.java.classLoader.getResource("web/index.html")
                    if (indexResource != null) {
                        call.respondText(indexResource.readText(), ContentType.Text.Html)
                    } else {
                        call.respondText("Not Found", ContentType.Text.Plain, HttpStatusCode.NotFound)
                    }
                }
            }
        }
    }.start(wait = true)
}
