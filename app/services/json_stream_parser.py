
import json
from typing import Any


class TopLevelJSONStreamParser:
    """
    Detecta propiedades completas de un objeto JSON
    recibido progresivamente mediante streaming.

    No emite valores parciales ni analiza recursivamente
    las propiedades internas.
    """

    def __init__(self):
        self.decoder = json.JSONDecoder()
        self.buffer = ""
        self.position = 0

        self.started = False
        self.finished = False

        self.state = "start"

    def feed(self, fragment: str) -> list[tuple[str, Any]]:
        """
        Incorpora un fragmento y devuelve las propiedades
        que quedaron completamente disponibles.
        """

        if self.finished:
            raise ValueError("El parser ya finalizó.")

        self.buffer += fragment

        completed = []

        while True:

            self._skip_whitespace()

            # ------------------------------------------
            # Inicio del objeto JSON
            # ------------------------------------------

            if self.state == "start":

                if self.position >= len(self.buffer):
                    break

                if self.buffer[self.position] != "{":
                    raise ValueError(
                        "La respuesta JSON debe comenzar con '{'."
                    )

                self.position += 1
                self.started = True
                self.state = "key"

            # ------------------------------------------
            # Leer nombre de propiedad
            # ------------------------------------------

            elif self.state == "key":

                if self.position >= len(self.buffer):
                    break

                try:
                    key, end = self.decoder.raw_decode(
                        self.buffer,
                        self.position
                    )

                except json.JSONDecodeError:
                    break

                if not isinstance(key, str):
                    raise ValueError(
                        "Se esperaba el nombre de una propiedad JSON."
                    )

                self.current_key = key
                self.position = end
                self.state = "colon"

            # ------------------------------------------
            # Esperar dos puntos
            # ------------------------------------------

            elif self.state == "colon":

                if self.position >= len(self.buffer):
                    break

                if self.buffer[self.position] != ":":
                    raise ValueError(
                        "Se esperaba ':' después de la propiedad."
                    )

                self.position += 1
                self.state = "value"

            # ------------------------------------------
            # Leer valor completo
            # ------------------------------------------

            elif self.state == "value":

                if self.position >= len(self.buffer):
                    break

                try:
                    value, end = self.decoder.raw_decode(
                        self.buffer,
                        self.position
                    )

                except json.JSONDecodeError:
                    break

                self.position = end

                completed.append(
                    (self.current_key, value)
                )

                self.state = "delimiter"

            # ------------------------------------------
            # Comprobar separador o fin del objeto
            # ------------------------------------------

            elif self.state == "delimiter":

                if self.position >= len(self.buffer):
                    break

                char = self.buffer[self.position]

                if char == ",":
                    self.position += 1
                    self.state = "key"

                elif char == "}":
                    self.position += 1
                    self.state = "finished"
                    self.finished = True
                    break

                else:
                    raise ValueError(
                        "Separador JSON inválido."
                    )

            elif self.state == "finished":
                break

        return completed

    def finish(self):
        """
        Verifica que se haya recibido el objeto JSON completo.
        """

        self._skip_whitespace()

        if not self.started or not self.finished:
            raise ValueError(
                "La respuesta JSON quedó incompleta."
            )

        if self.buffer[self.position:].strip():
            raise ValueError(
                "Se encontraron datos después del objeto JSON."
            )

    def _skip_whitespace(self):
        while (
            self.position < len(self.buffer)
            and self.buffer[self.position].isspace()
        ):
            self.position += 1
