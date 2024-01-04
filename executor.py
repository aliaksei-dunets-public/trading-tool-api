from trading_core.handler import ExchangeHandler
import trading_core.common as cmn

handler = ExchangeHandler.get_handler(trader_id="658048536aed0b022350af0b")
symbol = "SOLUSDT"

leverage_mdl = cmn.LeverageModel(
    session_id="1",
    account_id="USDT",
    symbol=symbol,
    side=cmn.OrderSideType.sell,
    quantity=0.5,
)
created_leverage = handler.create_leverage(position_mdl=leverage_mdl)
print(created_leverage)

print(handler.get_open_position(symbol=symbol, order_id=created_leverage.order_id))

print(handler.get_close_position(symbol=symbol, order_id=created_leverage.order_id))

close_position = handler.close_leverage(
    symbol=symbol, order_id=created_leverage.order_id
)
print(close_position)

# print(handler.get_close_position(symbol=symbol, order_id=close_position.order_id))

print(handler.get_close_position(symbol=symbol, order_id=created_leverage.order_id))

# open_position = handler.get_open_leverages(
#     symbol="SOLUSDT", position_id="65955d43ad237eee82671f9f"
# )

# print(open_position)

# print(
#     handler.get_close_leverages(
#         order_id="96bcb6fd-7c53-47cd-92fd-e90332d8ba9e",
#         symbol="SOLUSDT",
#     )
# )

# print(handler.get_open_orders(symbol=symbol))

# print(handler.get_close_leverages(symbol=symbol))
