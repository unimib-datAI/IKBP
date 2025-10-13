import { Router } from "express";
import { asyncRoute } from "../utils/async-route";
import { AnnotationSet } from "../models/annotationSet";
import { DocumentController } from "../controllers/document";
import { ChatController } from "../controllers/chat.js";
import { validateRequest } from "zod-express-middleware";
import { z } from "zod";

const route = Router();

export default (app) => {
    // route base root
    app.use("/save", route);

    /**
     * Save entity annotation set and optionally document features
     */
    route.post(
        "/",
        validateRequest({
            req: {
                body: z.object({
                    docId: z.union([z.string(), z.number()]),
                    annotationSets: z.object(),
                    features: z.object().optional(),
                }),
            },
        }),
        asyncRoute(async (req, res) => {
            console.log("=== SAVE ENDPOINT CALLED ===");
            console.log("Request body:", JSON.stringify(req.body, null, 2));

            const { docId, annotationSets, features } = req.body;

            console.log("Extracted docId:", docId);
            console.log(
                "Extracted annotationSets:",
                annotationSets ? "Present" : "Not present",
            );
            console.log(
                "Extracted features:",
                features
                    ? JSON.stringify(features, null, 2)
                    : "Not present or undefined",
            );
            console.log("Features type:", typeof features);
            console.log("Features === undefined:", features === undefined);

            // Update annotation sets
            console.log("Updating annotation sets...");
            const resUpdate =
                await DocumentController.updateEntitiesAnnotationSet(
                    docId,
                    annotationSets,
                );
            console.log("Annotation sets updated successfully");

            // Update features if provided
            let featuresUpdateResult = null;
            console.log("Checking if features should be updated...");
            if (features !== undefined) {
                console.log(
                    "Features is not undefined, proceeding with features update...",
                );
                console.log(
                    "Features to save:",
                    JSON.stringify(features, null, 2),
                );
                featuresUpdateResult =
                    await DocumentController.updateDocumentFeatures(
                        docId,
                        features,
                    );
                console.log(
                    "Features update completed. Result:",
                    featuresUpdateResult ? "Success" : "Failed",
                );
            } else {
                console.log("Features is undefined, skipping features update");
            }

            // Return both annotation sets and features information
            const response = {
                annotationSets: resUpdate,
                features: featuresUpdateResult
                    ? featuresUpdateResult.features
                    : undefined,
                success: true,
            };

            console.log("Sending response:", JSON.stringify(response, null, 2));
            console.log("=== SAVE ENDPOINT COMPLETED ===");

            return res.json(response);
        }),
    );

    route.post(
        "/rate-conversation",
        asyncRoute(async (req, res) => {
            const { rateValue, chatState } = req.body;
            const resAdd = await ChatController.saveRating(
                rateValue,
                chatState,
            );
            return res.json(resAdd);
        }),
    );
};
