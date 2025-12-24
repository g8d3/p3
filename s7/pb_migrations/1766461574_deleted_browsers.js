/// <reference path="../pb_data/types.d.ts" />
migrate((db) => {
  const dao = new Dao(db);
  const collection = dao.findCollectionByNameOrId("q9nktc1l9gp4724");

  return dao.deleteCollection(collection);
}, (db) => {
  const collection = new Collection({
    "id": "q9nktc1l9gp4724",
    "created": "2025-12-23 02:39:58.772Z",
    "updated": "2025-12-23 02:39:58.772Z",
    "name": "browsers",
    "type": "base",
    "system": false,
    "schema": [
      {
        "system": false,
        "id": "y0ecvhcc",
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
        "id": "q4akqxas",
        "name": "cdp_url",
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
        "id": "exyojdao",
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
