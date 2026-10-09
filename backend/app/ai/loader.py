class ModelLoader:

    def __init__(self):

        self.model = None

    def load(self):

        if self.model:

            return self.model

        print("Loading AI Voice Model...")

        # The real model will be initialized here later.
        self.model = object()

        print("Model Ready.")

        return self.model


loader = ModelLoader()