from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from apps.gestion.models import Venta
from apps.gestion.statistics import mes_actual, ranking_empleados
from apps.usuarios.models import Usuario


class EmpleadoMesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dueno = Usuario.objects.create_user('jefe', 'jefe@example.test', rol='dueno')
        cls.luis = Usuario.objects.create_user('luis', 'luis@example.test', first_name='Luis')
        cls.pedro = Usuario.objects.create_user('pedro', 'pedro@example.test', first_name='Pedro')
        cls.maria = Usuario.objects.create_user('maria', 'maria@example.test', first_name='María')

    def venta(self, usuario, total, fecha=date(2026, 10, 15)):
        return Venta.objects.create(usuario=usuario, total=total, fecha=fecha)

    def ranking(self, mes=date(2026, 10, 1)):
        return list(ranking_empleados(mes))

    def test_monto_es_criterio_y_excluye_dueno(self):
        self.venta(self.luis, 450000); self.venta(self.pedro, 510000); self.venta(self.maria, 480000)
        self.venta(self.dueno, 999999)
        with self.assertNumQueries(1):
            ranking = self.ranking()
        self.assertEqual([r['usuario_id'] for r in ranking], [self.pedro.pk, self.maria.pk, self.luis.pk])
        self.assertEqual(ranking[0]['total_vendido'], 510000)

    def test_desempate_por_cantidad_y_id_estable(self):
        self.venta(self.luis, 100); self.venta(self.pedro, 50); self.venta(self.pedro, 50)
        self.venta(self.maria, 25); self.venta(self.maria, 75)
        self.assertEqual([r['usuario_id'] for r in self.ranking()], [self.pedro.pk, self.maria.pk, self.luis.pk])

    def test_limites_calendario_y_diciembre(self):
        self.venta(self.luis, 100, date(2026, 9, 30))
        self.venta(self.pedro, 200, date(2026, 10, 1))
        self.venta(self.pedro, 300, date(2026, 10, 31))
        self.venta(self.maria, 999, date(2026, 11, 1))
        self.venta(self.luis, 50, date(2026, 12, 31))
        self.venta(self.maria, 999, date(2027, 1, 1))
        self.assertEqual(self.ranking()[0]['total_vendido'], 500)
        self.assertEqual(len(self.ranking()), 1)
        self.assertEqual(self.ranking(date(2026, 12, 1))[0]['usuario_id'], self.luis.pk)

    def test_inactivo_conserva_resultado_historico_y_clp(self):
        self.venta(self.pedro, 510000)
        self.pedro.is_active = False; self.pedro.save()
        self.client.force_login(self.dueno)
        respuesta = self.client.get(reverse('empleado_mes'), {'mes': '2026-10'})
        self.assertContains(respuesta, 'Pedro')
        self.assertContains(respuesta, '$510.000')
        self.assertContains(respuesta, 'resultado histórico')
        self.assertFalse(respuesta.context['destacado']['usuario__is_active'])

    def test_mes_sin_ventas_o_solo_dueno(self):
        self.venta(self.dueno, 500)
        self.assertEqual(self.ranking(), [])
        self.client.force_login(self.dueno)
        self.assertContains(self.client.get(reverse('empleado_mes'), {'mes': '2026-10'}),
                            'No hay ventas de empleados en este mes.')

    def test_mes_actual_en_santiago_no_utc(self):
        with patch('apps.gestion.statistics.timezone.now', return_value=datetime(2026, 12, 1, 1, tzinfo=dt_timezone.utc)):
            self.assertEqual(mes_actual(), date(2026, 11, 1))
            self.client.force_login(self.dueno)
            respuesta = self.client.get(reverse('empleado_mes'))
            self.assertEqual(respuesta.context['mes_evaluado'], date(2026, 11, 1))

    def test_mes_invalido_y_futuro_no_muestran_ranking(self):
        self.client.force_login(self.dueno)
        for mes in ('error', '2026-13', '9999-12', '2026-10-15', ''):
            respuesta = self.client.get(reverse('empleado_mes'), {'mes': mes})
            self.assertTrue(respuesta.context['mes_form'].errors)
            self.assertNotIn('ranking', respuesta.context)

    def test_empleado_no_accede_ni_recibe_estadisticas_globales(self):
        self.assertEqual(self.client.get(reverse('empleado_mes')).status_code, 302)
        self.client.force_login(self.luis)
        self.assertEqual(self.client.get(reverse('empleado_mes')).status_code, 403)
        self.assertNotContains(self.client.get('/'), 'Empleado del mes')
        self.assertNotIn('ranking', self.client.get('/').context)
