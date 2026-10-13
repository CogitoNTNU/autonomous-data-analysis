export class InvalidConversationMessage extends Error {
  constructor() {
    super("Meldingen må ha en rolle og innhold");
    this.name = "InvalidConversationMessage";
  }
}

export class InvalidDatasetReference extends Error {
  constructor() {
    super("Datasettet mangler id, versjon eller sti");
    this.name = "InvalidDatasetReference";
  }
}
