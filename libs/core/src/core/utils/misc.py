from beartype import BeartypeConf, BeartypeStrategy, beartype

# this decorator is used to disable beartype checks on specific classes that cause problems
nobeartype = beartype(conf=BeartypeConf(strategy=BeartypeStrategy.O0))
