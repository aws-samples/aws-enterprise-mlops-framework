## StableDiffusion ModelBuild Project Template

This is a sample code repository that demonstrates how the text to image model StableDiffusion can be fine-tuned, using the DreamBooth approach with Amazon SageMaker pipelines.
The pipeline fine-tunes the model with the provided data. During the training step, the model will be evaluated at different checkpoints and the best one will be returned. If the score exceeds a certain threshold, the model will be registered. 

The pipeline requires the following parameters:
- `InputDataUrl`: A s3 path to the training images. They should be square and same sized. Usually 5 images are enough.
- `ClassToken`: A token (or tokens) describing the "class" of the object shown in the training images (e.g. "backpack" or "running shoes")