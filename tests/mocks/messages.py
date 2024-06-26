# from blue_lugia.managers.message import MessageManager
# from blue_lugia.models import MessageList
# from blue_lugia.models.message import Message


# class MockMessageManager(MessageManager):
#     def all(self, force_refresh: bool = False) -> MessageList:
#         return MessageList(
#             [
#                 Message.USER("Hello, world!"),
#                 Message.ASSISTANT(""),
#             ],
#             tokenizer=self.tokenizer,
#             logger=self.logger,
#         )
