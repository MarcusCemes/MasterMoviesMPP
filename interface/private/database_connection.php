<?php

error_reporting(E_COMPILE_ERROR);

$dbhost = "192.168.1.97";
$dbuser = "node";
$dbpass = "Omega";
$dbname = "MasterMoviesMPP";


$mysqli = new mysqli($dbhost, $dbuser, $dbpass);

if (!$mysqli->connect_errno) {
    $mysqli->select_db($dbname) or die(json_encode(array('error' => 'Server error: could not select the database', 'database_error' => $mysqli->error)));
} else {
    die(json_encode(array('error' => 'Server error: could not connect to the database', 'database_error' => $mysqli->connect_error)));
}

?>
