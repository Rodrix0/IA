import random

def execute(**kwargs):
    """
    Lanza dos dados y devuelve el resultado como string.
    """
    
    # Generar un número aleatorio entre 1 y 6 para cada dado
    dado1 = random.randint(1, 6)
    dado2 = random.randint(1, 6)

    # Calcular la suma de los resultados
    resultado = dado1 + dado2

    # Devolver el resultado como string
    return f"La suma de los dados es: {dado1} + {dado2} = {resultado}"