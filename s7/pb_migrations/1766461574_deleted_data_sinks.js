/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("prxv407arrisuzq");

  return dao.deleteCollection(collection);
}, (db) => {
  const collection = new Collection({
    "id": "prxv407arrisuzq",
    "created": "2025-12-23 02:40:44.273Z",
    "updated": "2025-12-23 02:40:44.273Z",
    "name": "data_sinks",
    "type": "base",
    "system": false,
    "schema": [
      {
        "system": false,
        "id": "ithgquhp",
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
        "id": "eplz1brj",
        "name": "type",
        "type": "select",
        "required": true,
        "presentable": false,
        "unique": false,
        "options": {
          "maxSelect": 1,
          "values": [
            "webhook",
            "s3",
            "pocketbase",
            "custom_api"
          ]
        }
      },
      {
        "system": false,
        "id": "jm4devhy",
        "name": "config",
        "type": "json",
        "required": false,
        "presentable": false,
        "unique": false,
        "options": {
          "maxSize": 2000000
        }
      },
      {
        "system": false,
        "id": "heqo4ake",
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
    "listRule": "@request.auth.id = owner.id",
    "viewRule": "@request.auth.id = owner.id",
    "createRule": "@request.auth.id != \"\"",
    "updateRule": "@request.auth.id = owner.id",
    "deleteRule": "@request.auth.id = owner.id",
    "options": {}
  });

  return Dao(db).saveCollection(collection);
})
