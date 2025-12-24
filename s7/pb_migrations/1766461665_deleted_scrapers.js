/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("pn0057dnexyrjch");

  return dao.deleteCollection(collection);
}, (db) => {
  const collection = new Collection({
    "id": "pn0057dnexyrjch",
    "created": "2025-12-23 03:47:38.372Z",
    "updated": "2025-12-23 03:47:38.372Z",
    "name": "scrapers",
    "type": "base",
    "system": false,
    "schema": [
      {
        "system": false,
        "id": "on7tx8ux",
        "name": "name",
        "type": "text",
        "required": true,
        "presentable": false,
        "unique": false,
        "options": {
          "min": null,
          "max": null,
          "pattern": ""
        }
      },
      {
        "system": false,
        "id": "tomhtu7m",
        "name": "url",
        "type": "url",
        "required": true,
        "presentable": false,
        "unique": false,
        "options": {
          "exceptDomains": null,
          "onlyDomains": null
        }
      },
      {
        "system": false,
        "id": "1rhamxf6",
        "name": "ai_model",
        "type": "relation",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "collectionId": "rq4elk5l81y69hf",
          "cascadeDelete": false,
          "minSelect": null,
          "maxSelect": 1,
          "displayFields": null
        }
      },
      {
        "system": false,
        "id": "u5sgbddm",
        "name": "browser",
        "type": "relation",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "collectionId": "eu99b4wat50h6kd",
          "cascadeDelete": false,
          "minSelect": null,
          "maxSelect": 1,
          "displayFields": null
        }
      },
      {
        "system": false,
        "id": "veiodagd",
        "name": "code",
        "type": "text",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "min": null,
          "max": null,
          "pattern": ""
        }
      },
      {
        "system": false,
        "id": "iwpwrlk0",
        "name": "discovery_options",
        "type": "json",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "maxSize": 1000000
        }
      },
      {
        "system": false,
        "id": "pdtky8nq",
        "name": "selected_option",
        "type": "text",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "min": null,
          "max": null,
          "pattern": ""
        }
      },
      {
        "system": false,
        "id": "1vphnblx",
        "name": "schedule",
        "type": "text",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "min": null,
          "max": null,
          "pattern": ""
        }
      },
      {
        "system": false,
        "id": "fiojj9kl",
        "name": "owner",
        "type": "relation",
        "required": true,
        "presentable": false,
        "unique": false,
        "options": {
          "collectionId": "_pb_users_auth_",
          "cascadeDelete": true,
          "minSelect": null,
          "maxSelect": 1,
          "displayFields": null
        }
      }
    ],
    "indexes": [],
    "listRule": "@request.auth.id != \"\"",
    "viewRule": "@request.auth.id = owner.id",
    "createRule": "@request.auth.id != \"\"",
    "updateRule": "@request.auth.id = owner.id",
    "deleteRule": "@request.auth.id = owner.id",
    "options": {}
  });

  return Dao(db).saveCollection(collection);
})
