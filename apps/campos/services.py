def asignar_valor(objeto, campo, valor):
    """
    Asigna un valor a cualquier modelo (Servicio, Producto, etc.)
    """
    from django.contrib.contenttypes.models import ContentType

    content_type = ContentType.objects.get_for_model(objeto)

    campo_valor, _ = CampoValor.objects.get_or_create(
        campo=campo,
        content_type=content_type,
        object_id=objeto.id
    )

    # lógica según tipo
    if campo.tipo == 'text':
        campo_valor.valor_texto = valor
    elif campo.tipo == 'number':
        campo_valor.valor_numero = valor

    campo_valor.save()